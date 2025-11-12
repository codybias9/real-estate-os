"""
Airflow REST API client for monitoring DAGs and pipeline status
"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ..config import get_settings


settings = get_settings()


class AirflowClient:
    """Client for interacting with Airflow REST API"""

    def __init__(self):
        self.base_url = settings.AIRFLOW_API_URL
        self.auth = (settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make request to Airflow API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                auth=self.auth,
                timeout=30.0,
                **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get_dags(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get list of all DAGs"""
        return await self._request(
            "GET",
            f"dags?limit={limit}&offset={offset}"
        )

    async def get_dag(self, dag_id: str) -> Dict[str, Any]:
        """Get specific DAG details"""
        return await self._request("GET", f"dags/{dag_id}")

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 25,
        offset: int = 0,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get DAG runs for a specific DAG"""
        params = {"limit": limit, "offset": offset}
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return await self._request("GET", f"dags/{dag_id}/dagRuns?{query}")

    async def get_dag_run(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Get specific DAG run details"""
        return await self._request(
            "GET",
            f"dags/{dag_id}/dagRuns/{dag_run_id}"
        )

    async def get_task_instances(
        self,
        dag_id: str,
        dag_run_id: str
    ) -> Dict[str, Any]:
        """Get task instances for a DAG run"""
        return await self._request(
            "GET",
            f"dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
        )

    async def trigger_dag(
        self,
        dag_id: str,
        conf: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Trigger a DAG run"""
        payload = {"conf": conf or {}}
        return await self._request(
            "POST",
            f"dags/{dag_id}/dagRuns",
            json=payload
        )

    async def get_dag_stats(self) -> Dict[str, Any]:
        """Get aggregated DAG statistics"""
        try:
            dags_response = await self.get_dags(limit=100)
            dags = dags_response.get("dags", [])

            stats = {
                "total_dags": len(dags),
                "active_dags": sum(1 for dag in dags if not dag.get("is_paused")),
                "paused_dags": sum(1 for dag in dags if dag.get("is_paused")),
                "dags": []
            }

            # Get recent runs for each DAG
            for dag in dags:
                dag_id = dag["dag_id"]
                try:
                    runs = await self.get_dag_runs(dag_id, limit=10)
                    dag_runs = runs.get("dag_runs", [])

                    recent_runs = []
                    for run in dag_runs[:5]:  # Last 5 runs
                        recent_runs.append({
                            "dag_run_id": run.get("dag_run_id"),
                            "state": run.get("state"),
                            "execution_date": run.get("execution_date"),
                            "start_date": run.get("start_date"),
                            "end_date": run.get("end_date")
                        })

                    stats["dags"].append({
                        "dag_id": dag_id,
                        "is_paused": dag.get("is_paused"),
                        "is_active": dag.get("is_active"),
                        "last_parsed_time": dag.get("last_parsed_time"),
                        "recent_runs": recent_runs,
                        "success_count": sum(1 for r in dag_runs if r.get("state") == "success"),
                        "failed_count": sum(1 for r in dag_runs if r.get("state") == "failed"),
                        "running_count": sum(1 for r in dag_runs if r.get("state") == "running")
                    })
                except Exception as e:
                    print(f"Error fetching runs for DAG {dag_id}: {e}")
                    stats["dags"].append({
                        "dag_id": dag_id,
                        "is_paused": dag.get("is_paused"),
                        "error": str(e)
                    })

            return stats
        except Exception as e:
            return {"error": str(e), "total_dags": 0, "dags": []}

    async def get_health(self) -> Dict[str, Any]:
        """Get Airflow health status"""
        try:
            # Try to get version as health check
            response = await self._request("GET", "version")
            return {
                "status": "healthy",
                "version": response.get("version"),
                "git_version": response.get("git_version")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Singleton instance
airflow_client = AirflowClient()
