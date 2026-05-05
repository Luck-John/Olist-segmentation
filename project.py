#!/usr/bin/env python
"""
Utility script to manage common project tasks
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed!")
        return False
    except FileNotFoundError:
        print(f"\n❌ Command not found: {cmd[0]}")
        return False


def install_dependencies():
    """Install project dependencies"""
    return run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "Installing dependencies"
    )


def run_tests():
    """Run all tests with coverage"""
    return run_command(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--cov=src", "--cov-report=html"],
        "Running tests with coverage"
    )


def run_pipeline():
    """Run the main pipeline"""
    return run_command(
        [sys.executable, "scripts/run_pipeline.py"],
        "Running main pipeline"
    )


def lint_code():
    """Run code quality checks"""
    print(f"\n{'='*60}")
    print("📋 Running code quality checks")
    print(f"{'='*60}\n")
    
    commands = [
        ([sys.executable, "-m", "flake8", "src", "tests"], "Flake8 linting"),
        ([sys.executable, "-m", "black", "--check", "src", "tests"], "Black formatting"),
        ([sys.executable, "-m", "isort", "--check-only", "src", "tests"], "Import sorting"),
    ]
    
    all_passed = True
    for cmd, desc in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✅ {desc} passed")
        except subprocess.CalledProcessError:
            print(f"⚠️  {desc} has issues")
            all_passed = False
        except FileNotFoundError:
            print(f"⚠️  {desc} not installed")
    
    return all_passed


def format_code():
    """Format code with black and isort"""
    print(f"\n{'='*60}")
    print("📋 Formatting code")
    print(f"{'='*60}\n")
    
    commands = [
        ([sys.executable, "-m", "black", "src", "tests"], "Black formatting"),
        ([sys.executable, "-m", "isort", "src", "tests"], "Sorting imports"),
    ]
    
    for cmd, desc in commands:
        run_command(cmd, desc)


def start_mlflow():
    """Start MLFlow UI"""
    print(f"\n{'='*60}")
    print("📋 Starting MLFlow UI")
    print(f"{'='*60}")
    print("MLFlow UI: http://localhost:5000\n")
    
    subprocess.run([
        sys.executable, "-m", "mlflow", "server",
        "--backend-store-uri", "file:./mlruns",
        "--host", "0.0.0.0",
        "--port", "5000"
    ])


def docker_build():
    """Build Docker image"""
    return run_command(
        ["docker", "build", "-t", "olist-segmentation:latest", "-f", "docker/Dockerfile", "."],
        "Building Docker image"
    )


def docker_up():
    """Start Docker services"""
    os.chdir("docker")
    return run_command(
        ["docker-compose", "up", "-d"],
        "Starting Docker services"
    )


def docker_down():
    """Stop Docker services"""
    os.chdir("docker")
    return run_command(
        ["docker-compose", "down"],
        "Stopping Docker services"
    )


def show_help():
    """Show help message"""
    help_text = """
╔════════════════════════════════════════════════════════════════════╗
║  Olist Customer Segmentation - Project Management Script          ║
╚════════════════════════════════════════════════════════════════════╝

Usage: python project.py [command]

Commands:
  install       Install project dependencies
  test          Run tests with coverage report
  lint          Check code quality (flake8, black, isort)
  format        Format code (black, isort)
  pipeline      Run the main clustering pipeline
  mlflow        Start MLFlow UI server
  docker-build  Build Docker image
  docker-up     Start Docker services (docker-compose up)
  docker-down   Stop Docker services (docker-compose down)
  logs          Show Docker service logs
  help          Show this help message

Examples:
  python project.py install        # Install dependencies
  python project.py test           # Run all tests
  python project.py pipeline       # Execute pipeline
  python project.py mlflow         # Start MLFlow UI
  python project.py docker-up      # Start all services

For more information, see README.md
"""
    print(help_text)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return 0
    
    command = sys.argv[1].lower()
    
    commands = {
        'install': install_dependencies,
        'test': run_tests,
        'lint': lint_code,
        'format': format_code,
        'pipeline': run_pipeline,
        'mlflow': start_mlflow,
        'docker-build': docker_build,
        'docker-up': docker_up,
        'docker-down': docker_down,
        'help': show_help,
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}\n")
        show_help()
        return 1
    
    try:
        if command == 'help':
            commands[command]()
            return 0
        else:
            success = commands[command]()
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
