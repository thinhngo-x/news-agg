# News Aggregator MVP

A simple news aggregator with AI summ4. **Managing Feeds**:
   - Use the sidebar to add new RSS feeds
   - View active feeds in the statistics panel

5. **Reading Articles**:
   - Browse articles in the main feed
   - Click "📄 Full Content" to scrape the complete article
   - Click "🤖 AI Summary" to generate a summary (requires OpenAI API key)
   - Click "👁️ View Details" to see full article details

6. **AI Features**:
   - Configure your OpenAI API key directly in the UI (no need to edit files!)
   - Choose from multiple AI models based on your needs and budget
   - Use "🤖 Generate Summaries" to bulk process articles
   - Individual article summaries are available with the "🤖 AI Summary" buttont with Python and Streamlit.

## Features

- **RSS Feed Management**: Add and manage multiple RSS feeds
- **Article Fetching**: Automatically fetch articles from RSS feeds
- **Content Scraping**: Extract full article content from web pages
- **AI Summarization**: Generate concise summaries using OpenAI
- **Web Interface**: Clean, intuitive Streamlit-based UI
- **🆕 Dynamic API Key Management**: Configure OpenAI API key directly in the UI
- **🆕 AI Model Selection**: Choose from multiple OpenAI models (GPT-3.5, GPT-4, GPT-4o, etc.)
- **🆕 Real-time Status**: Visual indicators for API key status and current AI model

## Quick Start

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Setup the project**:
   ```bash
   cd news-agg
   uv sync
   ```

3. **Configure environment** (optional - can now be done via UI):
   ```bash
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```
   **OR** configure the OpenAI API key directly in the web interface!

4. **Run the application**:
   ```bash
   uv run streamlit run app.py
   ```

5. **Open in browser**: Navigate to http://localhost:8501

## Usage

1. **First Time Setup**:
   - The app comes with default RSS feeds (BBC, CNN, Reuters, etc.)
   - Click "🔄 Fetch New Articles" to load initial articles

2. **Configure OpenAI API Key** (New Feature!):
   - In the sidebar, expand "Configure OpenAI API Key"
   - Enter your OpenAI API key (get one from https://platform.openai.com/api-keys)
   - Click "💾 Save API Key" to save and validate
   - The status will show "✅ Configured" when set correctly
   - You can also clear the key using "🗑️ Clear API Key"

3. **Choose AI Model** (New Feature!):
   - Once API key is configured, select your preferred AI model
   - Available options: GPT-3.5 Turbo, GPT-4, GPT-4 Turbo, GPT-4o, GPT-4o Mini
   - Each model offers different quality/speed/cost trade-offs
   - Current model is displayed in the statistics panel

4. **Managing Feeds**:
   - Use the sidebar to add new RSS feeds
   - View active feeds in the statistics panel

4. **Reading Articles**:
   - Browse articles in the main feed
   - Click "📄 Full Content" to scrape the complete article
   - Click "🤖 AI Summary" to generate a summary (requires OpenAI API key)
   - Click "👁️ View Details" to see full article details

5. **AI Features**:
   - Configure your OpenAI API key directly in the UI (no need to edit files!)
   - Use "🤖 Generate Summaries" to bulk process articles
   - Individual article summaries are available with the "🤖 AI Summary" button

### 🤖 **AI Model Options:**

- **GPT-3.5 Turbo**: Fast and affordable, good for basic summaries
- **GPT-4**: High quality, more accurate but slower and more expensive
- **GPT-4 Turbo**: Balanced option with improved efficiency
- **GPT-4o**: Latest model with enhanced capabilities
- **GPT-4o Mini**: Efficient version of GPT-4o, good balance of quality and cost

Choose based on your needs:
- For high volume: GPT-3.5 Turbo or GPT-4o Mini
- For best quality: GPT-4 or GPT-4o
- For balanced use: GPT-4 Turbo

## Project Structure

```
news-agg/
├── app.py                 # Main Streamlit application
├── pyproject.toml         # Python project configuration
├── models/
│   └── database.py        # SQLite database models
├── services/
│   ├── feed_manager.py    # RSS feed management
│   ├── content_scraper.py # Web scraping functionality
│   └── ai_summarizer.py   # AI summarization
└── config/
    └── settings.py        # Application settings
```

## Configuration

Key settings in `config/settings.py`:
- **Database**: SQLite database path
- **API Keys**: OpenAI API key configuration
- **Default Feeds**: Pre-configured RSS feeds
- **UI Settings**: Items per page, summary length

## Dependencies

- **streamlit**: Web interface framework
- **feedparser**: RSS feed parsing
- **requests**: HTTP requests for web scraping
- **beautifulsoup4**: HTML parsing and content extraction
- **openai**: AI summarization (optional)
- **python-dotenv**: Environment variable management

## Notes

This is an MVP implementation that demonstrates the core functionality. For production use, consider:

- Adding user authentication
- Implementing caching and rate limiting
- Using a more robust database (PostgreSQL)
- Adding proper error handling and logging
- Implementing the Puppeteer MCP integration as mentioned in the original proposal
- Adding content deduplication
- Implementing full-text search
- Adding export functionality

## Troubleshooting

- **No articles showing**: Click "🔄 Fetch New Articles" to load content
- **AI summarization not working**: Check that OPENAI_API_KEY is set in .env file
- **Content scraping fails**: Some websites block automated scraping
- **Feed errors**: Some RSS feeds may be temporarily unavailable
