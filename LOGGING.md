# Logging Configuration

Logs are stored in `logs/` directory with the following structure:

## Log Levels

- **DEBUG**: Detailed information, typically of interest only when diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: An indication that something unexpected happened, or indicative of some problem in the near future
- **ERROR**: A serious problem, something has failed
- **CRITICAL**: A very serious error, possibly indicating the program itself may fail

## Log Files

- `segmentation.log`: Main application log file
- `pipeline_{timestamp}.log`: Pipeline execution logs
- `mlflow_{timestamp}.log`: MLFlow tracking logs

## Log Configuration

Configure logging in `config/config.yaml`:

```yaml
logging:
  level: "INFO"              # Log level
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  log_file: "logs/segmentation.log"
```

## Viewing Logs

```bash
# View recent logs
tail -f logs/segmentation.log

# View all logs
cat logs/segmentation.log

# Search for errors
grep ERROR logs/segmentation.log

# Real-time logs during Docker execution
docker-compose logs -f pipeline
```

## Log Retention

Logs are rotated automatically to prevent excessive disk usage:
- Keep 10 backup files
- Each file up to 10MB

Configure in the application as needed.
