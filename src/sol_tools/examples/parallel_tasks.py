"""
Examples demonstrating the parallel task processing framework.

This module contains example code showing how to use the parallel task processing
framework for various common scenarios.
"""

import time
import random
import logging
from typing import List, Dict, Any

# Import the async module components
import sol_tools.core.async as parallel

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def example_task(task_id: str, duration: float, fail_probability: float = 0.0) -> Dict[str, Any]:
    """
    Example task that simulates work by sleeping.
    
    Args:
        task_id: Identifier for the task
        duration: How long the task should take (in seconds)
        fail_probability: Probability of task failure (0.0 to 1.0)
        
    Returns:
        Dictionary with task results
        
    Raises:
        RuntimeError: If the task fails (based on fail_probability)
    """
    logger.info(f"Starting task {task_id}")
    
    # Simulate task that reports progress
    start_time = time.time()
    steps = 10
    step_duration = duration / steps
    
    for step in range(steps):
        # Sleep for a portion of the total duration
        time.sleep(step_duration)
        
        # Report progress (this will be captured if using progress_callback)
        progress = (step + 1) / steps * 100
        logger.info(f"Task {task_id} progress: {progress:.1f}%")
        
        # Simulate random failure
        if random.random() < fail_probability:
            logger.error(f"Task {task_id} failed at {progress:.1f}%")
            raise RuntimeError(f"Task {task_id} failed at {progress:.1f}%")
    
    # Task completed successfully
    elapsed = time.time() - start_time
    logger.info(f"Completed task {task_id} in {elapsed:.2f} seconds")
    
    # Return some result data
    return {
        "task_id": task_id,
        "duration": elapsed,
        "steps_completed": steps,
        "result_value": random.randint(1, 100)
    }

def progress_callback(task, progress, is_complete, status_message=None):
    """
    Example progress callback function.
    
    Args:
        task: The task being updated
        progress: Progress percentage (0-100)
        is_complete: Whether the task is complete
        status_message: Optional status message
    """
    task_id = task.task_id
    if is_complete:
        logger.info(f"Task {task_id} completed: {progress:.1f}% - {status_message or 'Done'}")
    else:
        logger.info(f"Task {task_id} progress: {progress:.1f}% - {status_message or ''}")

def example_1_basic_task():
    """Example of submitting a single task."""
    logger.info("Running Example 1: Basic Task Submission")
    
    # Submit a task
    task = parallel.submit_task(
        example_task,
        "basic-task",
        duration=2.0,
        progress_callback=progress_callback
    )
    
    # Wait for the task to complete
    logger.info(f"Waiting for task {task.task_id} to complete...")
    task_status = parallel.wait_for_task(task.task_id)
    
    # Check the result
    if task.is_complete and task.success:
        logger.info(f"Task completed successfully with result: {task.result.value}")
    else:
        logger.error(f"Task failed with error: {task.result.error}")
    
    logger.info("Example 1 completed\n")

def example_2_parallel_execution():
    """Example of executing multiple tasks in parallel."""
    logger.info("Running Example 2: Parallel Execution")
    
    # Create a list of tasks to execute
    tasks = []
    for i in range(5):
        # Create tasks with varying durations
        task_func = lambda idx=i: example_task(
            f"parallel-{idx}", 
            duration=random.uniform(1.0, 3.0),
            fail_probability=0.2
        )
        tasks.append(task_func)
    
    # Execute tasks in parallel and get aggregated results
    logger.info(f"Executing {len(tasks)} tasks in parallel...")
    results = parallel.execute_in_parallel(tasks, aggregate_results=True)
    
    # Process the results
    if isinstance(results, parallel.ResultAggregator):
        logger.info(f"Completed {results.success_count()} tasks successfully")
        logger.info(f"Failed {results.failure_count()} tasks")
        
        # Get successful results
        successful_results = results.get_successful_results()
        for task, result in successful_results:
            logger.info(f"Task {task.task_id} result: {result}")
        
        # Get failed results
        failed_results = results.get_failed_results()
        for task, _ in failed_results:
            logger.error(f"Task {task.task_id} failed with error: {task.result.error}")
    
    logger.info("Example 2 completed\n")

def example_3_task_priorities():
    """Example demonstrating task priorities."""
    logger.info("Running Example 3: Task Priorities")
    
    # Configure async with limited workers to demonstrate priority
    parallel.configure_async(max_threads=2)
    
    # Submit tasks with different priorities
    tasks = []
    
    # Low priority tasks
    for i in range(3):
        task = parallel.submit_task(
            example_task,
            f"low-priority-{i}",
            duration=2.0,
            priority=parallel.TaskPriority.LOW
        )
        tasks.append(task)
        logger.info(f"Submitted low priority task: {task.task_id}")
    
    # High priority task should execute before low priority tasks
    high_priority_task = parallel.submit_task(
        example_task,
        "high-priority",
        duration=1.0,
        priority=parallel.TaskPriority.HIGH
    )
    tasks.append(high_priority_task)
    logger.info(f"Submitted high priority task: {high_priority_task.task_id}")
    
    # Wait for all tasks to complete
    logger.info("Waiting for all tasks to complete...")
    for task in tasks:
        parallel.wait_for_task(task.task_id)
    
    logger.info("Example 3 completed\n")

def example_4_task_cancellation():
    """Example demonstrating task cancellation."""
    logger.info("Running Example 4: Task Cancellation")
    
    # Submit a long-running task
    long_task = parallel.submit_task(
        example_task,
        "long-running",
        duration=10.0
    )
    logger.info(f"Submitted long-running task: {long_task.task_id}")
    
    # Let it run for a bit
    logger.info("Letting task run for 2 seconds...")
    time.sleep(2.0)
    
    # Cancel the task
    logger.info(f"Cancelling task {long_task.task_id}...")
    cancelled = parallel.cancel_task(long_task.task_id)
    
    if cancelled:
        logger.info(f"Task {long_task.task_id} was cancelled successfully")
    else:
        logger.warning(f"Failed to cancel task {long_task.task_id}")
    
    # Check the task status
    task_status = parallel.wait_for_task(long_task.task_id, timeout=1.0)
    logger.info(f"Task status: {task_status}")
    
    logger.info("Example 4 completed\n")

def example_5_process_workers():
    """Example using process workers for CPU-bound tasks."""
    logger.info("Running Example 5: Process Workers")
    
    # Define a CPU-bound task
    def cpu_intensive_task(iterations):
        """A CPU-intensive task that benefits from process workers."""
        logger.info(f"Starting CPU-intensive task with {iterations} iterations")
        result = 0
        for i in range(iterations):
            # Perform some CPU-intensive calculation
            result += sum(i * j for j in range(1000))
        logger.info(f"Completed CPU-intensive task")
        return result
    
    # Execute tasks using process workers
    tasks = []
    for i in range(4):
        task_func = lambda idx=i: cpu_intensive_task(100000 + idx * 10000)
        tasks.append(task_func)
    
    logger.info(f"Executing {len(tasks)} CPU-intensive tasks using process workers...")
    results = parallel.execute_in_parallel(tasks, use_processes=True)
    
    if isinstance(results, parallel.ResultAggregator):
        logger.info(f"All tasks completed: {results.success_count()} successful, {results.failure_count()} failed")
    
    logger.info("Example 5 completed\n")

def run_all_examples():
    """Run all examples in sequence."""
    try:
        # Configure async system
        parallel.configure_async(
            max_threads=4,
            max_processes=2,
            default_worker_type="thread",
            max_retries=2
        )
        
        # Run examples
        example_1_basic_task()
        example_2_parallel_execution()
        example_3_task_priorities()
        example_4_task_cancellation()
        example_5_process_workers()
        
    finally:
        # Always shut down the async system
        parallel.shutdown_async()

if __name__ == "__main__":
    run_all_examples() 