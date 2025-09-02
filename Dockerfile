FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /sol

# Copy the entire monorepo
COPY . .

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "conference_signup.py"]