"""
YOUTUBEDROP - Script Generator
================================
Converts topics, research, or transcripts into full YouTube video scripts
using LLM (Anthropic Claude or OpenAI GPT).
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SCRIPT_PROMPT = """You are an expert YouTube scriptwriter for the Resonance Energy channel.

Write a compelling, well-structured YouTube video script for the following topic:
TOPIC: {topic}

Additional context:
{context}

Script requirements:
- Hook (first 15 seconds — grab attention immediately)
- Intro (channel intro, what this video covers)
- Main content (3-5 key sections with clear transitions)
- Call to action (like, subscribe, comment prompt)
- Outro

Format:
[HOOK]
...

[INTRO]
...

[SECTION 1: Title]
...

[SECTION 2: Title]
...

[CTA]
...

[OUTRO]
...

Estimated runtime: {duration_min} minutes
Tone: {tone}
"""


class ScriptGenerator:
    """
    Generates YouTube scripts from topics using LLM.
    Supports Claude (Anthropic) and GPT (OpenAI).
    """

    def __init__(self, provider: str = "auto"):
        """
        provider: "anthropic", "openai", or "auto" (tries anthropic first)
        """
        self.provider = provider
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self._openai_key = os.getenv("OPENAI_API_KEY")
        logger.info(f"ScriptGenerator initialized (provider={provider})")

    def generate(
        self,
        topic: str,
        context: str = "",
        duration_min: int = 10,
        tone: str = "educational, energetic",
    ) -> Optional[str]:
        """Generate a full video script from a topic."""
        prompt = SCRIPT_PROMPT.format(
            topic=topic,
            context=context or "No additional context provided.",
            duration_min=duration_min,
            tone=tone,
        )

        if self.provider == "anthropic" or (self.provider == "auto" and self._anthropic_key):
            return self._generate_anthropic(prompt)
        elif self.provider == "openai" or (self.provider == "auto" and self._openai_key):
            return self._generate_openai(prompt)
        else:
            logger.error("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")
            return None

    def _generate_anthropic(self, prompt: str) -> Optional[str]:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._anthropic_key)
            msg = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            script = msg.content[0].text
            logger.info(f"Script generated via Anthropic ({len(script)} chars)")
            return script
        except ImportError:
            logger.warning("anthropic package not installed")
            return self._generate_openai(prompt)
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return None

    def _generate_openai(self, prompt: str) -> Optional[str]:
        try:
            import openai
            client = openai.OpenAI(api_key=self._openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            script = resp.choices[0].message.content
            logger.info(f"Script generated via OpenAI ({len(script)} chars)")
            return script
        except ImportError:
            logger.warning("openai package not installed")
            return None
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return None

    def generate_title_and_description(self, script: str, topic: str) -> dict:
        """Generate SEO-optimized title, description, and tags from a script."""
        prompt = f"""Given this YouTube video script about "{topic}", generate:
1. 3 title options (SEO-optimized, <60 chars, compelling)
2. Description (first 2 lines hook, then overview, 300 words max)
3. 10 relevant tags

Topic: {topic}
Script excerpt: {script[:500]}...

Respond as JSON:
{{
  "titles": ["Title 1", "Title 2", "Title 3"],
  "description": "...",
  "tags": ["tag1", "tag2", ...]
}}"""

        result = self.generate(prompt, duration_min=0, tone="professional")
        if result:
            import re
            import json
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return {"titles": [topic], "description": "", "tags": []}
