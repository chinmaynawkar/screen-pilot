"""
Firestore implementation of IRunRepository.

Stores runs in collection `runs` and steps in subcollection `runSteps` per run.
Uses ADC for credentials. See docs/chunk-1-firestore-repo-setup.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from google.cloud import firestore

from backend.app.config import get_settings
from backend.app.domain.models import (
    Action,
    ActionTarget,
    ActionType,
    Run,
    RunStatus,
    RunStep,
)
from backend.app.domain.ports import IRunRepository


class FirestoreRunRepository(IRunRepository):
    def __init__(self) -> None:
        """
        Initialize the FirestoreRunRepository with project settings.
        Configures the Firestore client using GCP project and database ID.
        """
        settings = get_settings()
        client_kw: dict = {"project": settings.gcp_project_id or None}
        if settings.firestore_database_id:
            client_kw["database"] = settings.firestore_database_id
        self._client = firestore.Client(**client_kw)
        self._runs_collection = settings.runs_collection
        self._steps_subcollection = settings.run_steps_subcollection

    def _runs_ref(self) -> firestore.CollectionReference:
        """
        Returns the Firestore collection reference for runs.
        """
        return self._client.collection(self._runs_collection)

    def _run_doc_ref(self, run_id: str) -> firestore.DocumentReference:
        """
        Returns the Firestore document reference for the specific run.
        """
        return self._runs_ref().document(run_id)

    def _steps_ref(self, run_id: str) -> firestore.CollectionReference:
        """
        Returns the Firestore collection reference for steps of a given run.
        """
        return self._run_doc_ref(run_id).collection(self._steps_subcollection)

    def _run_to_firestore_dict(self, run: Run) -> dict[str, Any]:
        """
        Converts a Run object to dictionary format suitable for Firestore storage.
        """
        return {
            "status": run.status.value,
            "taskType": run.task_type,
            "parameters": run.parameters,
            "createdAt": run.created_at,
            "updatedAt": run.updated_at,
            "stepsCount": len(run.steps),
        }

    def _run_from_firestore_dict(
        self, run_id: str, data: dict[str, Any], steps: list[RunStep]
    ) -> Run:
        """
        Constructs a Run object from Firestore document data and its steps.
        """
        status_val = data.get("status", "pending")
        created = data.get("createdAt")
        updated = data.get("updatedAt")
        return Run(
            id=run_id,
            task_type=data.get("taskType", "fill_timesheet"),
            parameters=data.get("parameters") or {},
            status=RunStatus(status_val),
            steps=steps,
            created_at=created if isinstance(created, datetime) else datetime.now(),
            updated_at=updated if isinstance(updated, datetime) else datetime.now(),
        )

    def _step_to_firestore_dict(self, step: RunStep) -> dict[str, Any]:
        """
        Converts a RunStep object to dictionary format suitable for Firestore storage.
        """
        return {
            "index": step.index,
            "action": {
                "action": step.action.action.value,
                "target": {
                    "type": step.action.target.type,
                    "text": step.action.target.text,
                    "label": step.action.target.label,
                    "placeholder": step.action.target.placeholder,
                    "x": step.action.target.x,
                    "y": step.action.target.y,
                },
                "value": step.action.value,
            },
            "reason": step.reason,
            "result": step.result,
            "screenshotUrl": step.screenshot_url,
        }

    def _step_from_firestore_dict(self, data: dict[str, Any]) -> RunStep:
        """
        Constructs a RunStep object from Firestore document data.
        """
        action_data = data.get("action") or {}
        target_data = action_data.get("target") or {}
        action = Action(
            action=ActionType(action_data.get("action", "click")),
            target=ActionTarget(
                type=target_data.get("type", "text"),
                text=target_data.get("text"),
                label=target_data.get("label"),
                placeholder=target_data.get("placeholder"),
                x=target_data.get("x"),
                y=target_data.get("y"),
            ),
            value=action_data.get("value"),
        )
        return RunStep(
            index=data["index"],
            action=action,
            reason=data.get("reason"),
            result=data.get("result", ""),
            screenshot_url=data.get("screenshotUrl"),
        )

    def create_run(self, run: Run) -> Run:
        """
        Persists a new run to Firestore.
        Returns the created run object.
        """
        doc_ref = self._run_doc_ref(run.id)
        doc_ref.set(self._run_to_firestore_dict(run))
        return run

    def update_run(self, run: Run) -> Run:
        """
        Updates an existing run in Firestore.
        Sets the updatedAt field to Firestore server timestamp.
        Returns the updated run object.
        """
        doc_ref = self._run_doc_ref(run.id)
        update_data = self._run_to_firestore_dict(run)
        update_data["updatedAt"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(update_data, merge=True)
        return run

    def append_step(self, run_id: str, step: RunStep) -> None:
        """
        Appends or updates a step document in the steps subcollection for a run.
        """
        steps_ref = self._steps_ref(run_id)
        doc_ref = steps_ref.document(str(step.index))
        doc_ref.set(self._step_to_firestore_dict(step), merge=True)

    def get_run(self, run_id: str) -> Optional[Run]:
        """
        Retrieves a run and its associated steps from Firestore.
        Returns Run object if found, otherwise None.
        """
        doc_ref = self._run_doc_ref(run_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        run_data = snapshot.to_dict() or {}
        steps_ref = self._steps_ref(run_id)
        step_docs = steps_ref.order_by("index").stream()
        steps: list[RunStep] = []
        for s in step_docs:
            steps.append(self._step_from_firestore_dict(s.to_dict() or {}))
        return self._run_from_firestore_dict(run_id, run_data, steps)
