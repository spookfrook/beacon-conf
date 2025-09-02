FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /sol

# Copy the entire monorepo
COPY . .

# Create voice_memos directory
RUN mkdir -p voice_memos

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "conference_signup:app", "--host", "0.0.0.0", "--port", "8000"]