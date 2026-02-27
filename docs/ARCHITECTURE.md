# ARCHITECTURE — YOUTUBEDROP

## Purpose
Automated YouTube content production and publishing pipeline. Converts ideas, research, and agent output into published video content.

## System Overview
```
[Idea/Script Gen] --> [Asset Pipeline] --> [Video Assembly]
[Upload Manager]  --> [YouTube API]   --> [Analytics Loop]
```

## Components
- **Script Generator**: LLM-based topic → script conversion
- **Asset Pipeline**: Thumbnail gen, b-roll sourcing, voiceover (TTS)
- **Video Assembly**: Automated editing/rendering (FFmpeg/Remotion)
- **Upload Manager**: YouTube Data API v3 integration
- **Analytics Loop**: Performance feedback into content strategy

## Data Flow
Topic → Script → Assets → Render → Upload → Monitor → Optimize

## Integration Points
- future-predictor-council (content topics)
- NATEBJONES (cross-promotion)
- NCL knowledge base (research source)

## Key Decisions
- Fully autonomous pipeline — human review gate before publish
- Modular stages allow partial automation
