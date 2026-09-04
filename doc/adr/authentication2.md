"""
 I suggest celery because of its complex workflows and most especially oga at the tops likes it, we can also consider RQ(Redis Queue). Celery is an open-source, asynchronous distributed task queue used in backend web development to handle time-consuming or resource-heavy jobs in the background

 The MVP will use **Celery** for asynchronous/background jobs.

A message broker will be used to queue tasks, with Redis being the default
MVP broker.

The API is responsible for creating/submitting jobs.

Celery workers are responsible for executing background tasks.

The API must not directly perform long-running video-processing work inside
the HTTP request lifecycle.

## Job Lifecycle

The domain-level job lifecycle will use the following terminology:

    pending
        Job has been created but has not started.

    processing
        Worker has started processing the job.

    completed
        Processing completed successfully.

    failed
        Processing failed.

The exact persistence representation may differ from Celery's internal task
state.

The application's `Job` entity is the source of truth for user-visible job
state.

Celery task state must not become the application's domain model.

## Job Ownership

Every user-created job must have an associated user/project.

Example:

    User
      |
      +-- Project
            |
            +-- Job

A user may only retrieve or manipulate jobs that they are authorized to
access.

## Task Responsibilities

A Celery task should:

1. Receive a job identifier.
2. Load the job from persistent storage.
3. Validate that the job is executable.
4. Change status to `processing`.
5. Execute the required operation.
6. Store the resulting output.
7. Mark the job as `completed`.

If processing fails:

1. Capture the failure.
2. Record an appropriate error state.
3. Mark the job as `failed`.
4. Preserve enough information for debugging without exposing sensitive data.


PROS:
- Mature
- Supports complex workflows 
- Large ecosystem i.e library, communities and resource.

CONS:
- More configuration and operational complexity

API PROVIDER:
 we can make use of the following OPENAPI:
 - GEMINI - we might likely face server hitch and likely updown time because of Traffic if we use free.

 - Groq - Also free I am not sure of future promblem with server because it worked perfectly well with my group's project.

 -Jan - Jan to run AI models completely for free and offline directly on your computer.

"""

