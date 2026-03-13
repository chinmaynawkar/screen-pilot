"""
Firestore implementation of IRunRepository.

Stores runs in collection `runs` and steps in subcollection `runSteps` per run.
Uses ADC for credentials. See docs/chunk-1-firestore-repo-setup.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
    StepSeverity,
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
            "plannerMode": run.planner_mode,
            "finalScreenshotUrl": run.final_screenshot_url,
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
            planner_mode=data.get("plannerMode"),
            steps=steps,
            final_screenshot_url=data.get("finalScreenshotUrl"),
            created_at=created
            if isinstance(created, datetime)
            else datetime.now(tz=timezone.utc),
            updated_at=updated
            if isinstance(updated, datetime)
            else datetime.now(tz=timezone.utc),
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
                "pressEnter": step.action.press_enter,
            },
            "reason": step.reason,
            "evidence": step.evidence,
            "result": step.result,
            "severity": step.severity.value,
            "attempt": step.attempt,
            "screenshotUrl": step.screenshot_url,
            "createdAt": step.created_at,
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
            press_enter=bool(action_data.get("pressEnter", False)),
        )
        return RunStep(
            index=data["index"],
            action=action,
            reason=data.get("reason"),
            evidence=data.get("evidence"),
            result=data.get("result", ""),
            severity=StepSeverity(data.get("severity", StepSeverity.INFO.value)),
            attempt=data.get("attempt"),
            screenshot_url=data.get("screenshotUrl"),
            created_at=data.get("createdAt")
            if isinstance(data.get("createdAt"), datetime)
            else datetime.now(tz=timezone.utc),
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
        Append a step document and keep parent stepsCount in sync.

        Uses a transaction so retries or duplicate writes of the same step index
        do not over-increment stepsCount.
        """
        run_ref = self._run_doc_ref(run_id)
        step_ref = self._steps_ref(run_id).document(str(step.index))

        transaction = self._client.transaction()

        @firestore.transactional
        def _append_step_txn(tx: firestore.Transaction) -> None:
            step_snapshot = step_ref.get(transaction=tx)
            if step_snapshot.exists:
                return
            tx.set(step_ref, self._step_to_firestore_dict(step), merge=True)
            tx.set(
                run_ref,
                {
                    "stepsCount": firestore.Increment(1),
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

        _append_step_txn(transaction)

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
