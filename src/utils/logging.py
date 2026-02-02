import logging
import sys

def get_logger(component_name: str) -> logging.Logger:
    """
    Create a logger for a specific component with formatted output.
    
    Args:
        component_name: Name of the component (e.g., 'monitor', 'planner')
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(component_name)
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            f'[%(asctime)s] [{component_name.upper()}] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


# Keep existing functions for backward compatibility
def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def log_day_header(day: int) -> None:
    print(f"\n{'='*60}")
    print(f"DAY {day}")
    print(f"{'='*60}")


def log_kpis(kpis: dict) -> None:
    for k, v in kpis.items():
        print(f"{k:<25} : {v}")
