# backend/tools/summarizer_tool.py

import os
import mimetypes
import openai
import PyPDF2
from newspaper import Article
from docx import Document
from dotenv import load_dotenv
from typing import List, Dict, Union, Tuple
from backend.schemas import WebSearchOutput, WebSearchResult

load_dotenv()

class SummarizerTool:
    CHAR_CHUNK_SIZE = 12000
    SUMMARY_RATIO = 0.5

    def __init__(self, prompt: str = None):
        self.default_prompt = prompt or (
            "As a professional summarization expert, create a concise and accurate summary "
            "that captures the essential information, key points, and critical insights. "
            "Prioritize clarity, coherence, and factual accuracy. Omit redundant information "
            "while preserving the original meaning and context. Format with clear paragraphs "
            "where appropriate."
        )
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run(self, input_data, context: dict = None, config: dict = None) -> str:
        print("🟡 SummarizerTool invoked")
        prompt = (config or {}).get("prompt", self.default_prompt)
        include_details = (config or {}).get("include_details", True)

        # 1) Gather text with source information
        source_data = self._gather_text(input_data)
        if not source_data:
            return "⚠️ No content to summarize"

        # 2) Calculate target summary length
        total_chars = sum(len(text) for _, text in source_data)
        target_final_length = max(100, min(2000, int(total_chars * self.SUMMARY_RATIO / 10)))

        # 3) Process each source
        source_summaries = []
        for source, text in source_data:
            if not text.strip():
                continue
                
            # Calculate source target length proportional to its content size
            source_target = max(50, min(800, int(len(text) * self.SUMMARY_RATIO / 10)))
            source_prompt = f"{prompt} Keep the summary to approximately {source_target} words."
            
            print(f"📑 Processing source: {source or 'Unknown'} ({len(text)} chars)")
            source_result = self._summarize_text(source_prompt, text)
            source_summaries.append({
                "source": source,
                "original_length": len(text),
                "summary": source_result,
                "summary_length": len(source_result.split())
            })

        # 4) Create final summary
        if not source_summaries:
            return "⚠️ No valid content processed"

        if len(source_summaries) == 1:
            print("✅ Single source - using as final summary")
            final_summary = source_summaries[0]["summary"]
        else:
            print(f"🔄 Combining {len(source_summaries)} source summaries")
            combined_text = "\n\n".join([f"Source: {s['source']}\nSummary: {s['summary']}" for s in source_summaries])
            final_prompt = (
                f"{prompt} Consolidate the key insights from these summaries into "
                f"a comprehensive overview. Keep the final summary to approximately "
                f"{target_final_length} words."
            )
            final_summary = self._summarize_text(final_prompt, combined_text)

        print(f"✅ Summarization complete. Final summary: {len(final_summary.split())} words")
        
        # Store detailed summaries in context if available
        if context is not None:
            context["summarizer_details"] = {
                "final_summary": final_summary,
                "source_summaries": source_summaries
            }

        return final_summary

    def _gather_text(self, input_data) -> List[Tuple[str, str]]:
        """Extract raw text with source information."""
        sources = []

        # WebSearchOutput - process each URL separately
        if isinstance(input_data, WebSearchOutput):
            print(f"🟢 Detected {len(input_data.results)} web results")
            for res in input_data.results:
                try:
                    art = Article(res.link)
                    art.download()
                    art.parse()
                    sources.append((res.link, f"Title: {art.title}\n{art.text}"))
                    print(f"   ✔️  Fetched: {res.link} ({len(art.text)} chars)")
                except Exception as e:
                    print(f"   ❌ Failed to fetch {res.link}: {str(e)[:70]}")

        # Single string input
        elif isinstance(input_data, str):
            print("🟢 Detected raw string input")
            sources.append(("Text Input", input_data))

        # File-like or bytes input
        elif hasattr(input_data, "filename") or isinstance(input_data, (bytes, bytearray)):
            print("🟢 Detected file input")
            try:
                text, source_name = self._extract_text_from_file(input_data)
                sources.append((source_name, text))
            except Exception as e:
                print(f"❌ File processing error: {str(e)[:70]}")

        else:
            print(f"❌ Unsupported input type: {type(input_data)}")

        return sources

    def _summarize_text(self, prompt: str, text: str) -> str:
        """Handle chunking and summarization for a text block"""
        if len(text) <= self.CHAR_CHUNK_SIZE:
            return self._call_llm(prompt, text)

        chunks = self._chunk_text(text)
        print(f"📑 Splitting into {len(chunks)} chunks for summarization")
        
        chunk_summaries = []
        for i, chunk in enumerate(chunks, 1):
            print(f"  ✳️ Summarizing chunk {i}/{len(chunks)} ({len(chunk)} chars)")
            chunk_summaries.append(self._call_llm(prompt, chunk))
        
        if len(chunk_summaries) == 1:
            return chunk_summaries[0]
        
        combined = "\n\n".join([f"Chunk {i+1}:\n{s}" for i, s in enumerate(chunk_summaries)])
        consolidation_prompt = (
            "Combine these partial summaries into a single coherent summary. "
            "Maintain all critical information while eliminating redundancies. "
            "Ensure smooth transitions between sections."
        )
        return self._call_llm(consolidation_prompt, combined)

    def _chunk_text(self, text: str) -> List[str]:
        """Split text preserving paragraph boundaries"""
        if len(text) <= self.CHAR_CHUNK_SIZE:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.CHAR_CHUNK_SIZE, len(text))
            
            # Prefer splitting at paragraph boundaries
            split_at = text.rfind("\n\n", start, end)
            if split_at < start + (self.CHAR_CHUNK_SIZE // 2):  # Don't make chunks too small
                split_at = text.rfind("\n", start, end)
            
            if split_at <= start:  # No good split point found
                split_at = end
                
            chunks.append(text[start:split_at].strip())
            start = split_at
            
        return chunks

    def _call_llm(self, prompt: str, text: str) -> str:
        """Handle LLM communication with error management"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ LLM error: {str(e)[:100]}")
            return f"⚠️ Summarization failed: {str(e)[:70]}"

    def _extract_text_from_file(self, file) -> Tuple[str, str]:
        """Extract text from various file formats with source info"""
        # Handle different file types
        stream = getattr(file, "file", file)
        name = getattr(file, "filename", "Uploaded File")
        mime, _ = mimetypes.guess_type(name or "")

        try:
            if mime == "application/pdf":
                reader = PyPDF2.PdfReader(stream)
                text = "\n".join(p.extract_text() or "" for p in reader.pages)
                return text, f"PDF: {name}"

            elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc = Document(stream)
                text = "\n".join(p.text for p in doc.paragraphs)
                return text, f"DOCX: {name}"

            elif mime in ["text/plain", "text/markdown", "text/csv"]:
                stream.seek(0)
                return stream.read().decode("utf-8", errors="ignore"), f"Text: {name}"

            else:
                stream.seek(0)
                raw = stream.read()
                if isinstance(raw, (bytes, bytearray)):
                    return raw.decode("utf-8", errors="ignore"), f"File: {name}"
                return str(raw), f"File: {name}"

        except Exception as e:
            raise RuntimeError(f"File processing error ({name}): {str(e)}")