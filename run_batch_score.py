"""Batch score pending jobs with rate limiting"""
from job_matcher import JobMatcher, Config
import time

config = Config()
config.batch_size = 1500  # Process all remaining jobs
config.rate_limit_seconds = 1.5  # Safe rate limit for OpenAI

print("="*60)
print("Starting batch scoring: 50 jobs, 1.5s delay")
print("Prioritized by freshness (newest jobs first)")
print("="*60)
print("Starting batch scoring: 50 jobs, 1.5s delay")
print("="*60)

try:
    matcher = JobMatcher(config)
    result = matcher.process_batch()
    print(f"\nComplete! Processed: {result['processed']}, Qualified: {result['qualified']}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
