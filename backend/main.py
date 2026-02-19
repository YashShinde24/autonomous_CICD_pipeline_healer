"""
Production-ready FastAPI backend for DevOps AI Command Center
With WebSocket support for real-time pipeline updates
"""

import os
import asyncio
import json
import threading
from datetime import datetime
from uuid import uuid4
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Supabase imports
from supabase import create_client, Client

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
supabase: Optional[Client] = None
if supabase_url and supabase_service_key:
    supabase = create_client(supabase_url, supabase_service_key)

app = FastAPI(title="DevOps AI Command Center API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Data Models ==============

class PipelineStatusEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RunCreate(BaseModel):
    repo_url: str
    branch: str = "main"
    team_id: Optional[str] = None


class RunResponse(BaseModel):
    id: str
    repo_url: str
    branch: str
    status: str
    progress: float
    current_step: str
    total_failures: int
    total_fixes: int
    iterations_used: int
    score: float
    total_time_seconds: int
    created_at: datetime
    logs: List[str] = []


class PipelineUpdate(BaseModel):
    run_id: str
    status: str
    progress: float
    current_step: str
    iteration: int
    failures_detected: List[Dict[str, Any]] = []
    fixes_applied: List[Dict[str, Any]] = []
    logs: List[str] = []
    ci_status: str = "UNKNOWN"
    score: Optional[float] = None


# ============== In-Memory Storage ==============

# Pipeline runs storage (use Redis in production)
pipeline_runs: Dict[str, Dict[str, Any]] = {}
pipeline_logs: Dict[str, List[str]] = {}
websocket_connections: Dict[str, List[WebSocket]] = {}


# ============== WebSocket Manager ==============

class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_update(self, update: Dict[str, Any]):
        """Send update to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(update)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_run(self, run_id: str, update: Dict[str, Any]):
        """Send update to specific run subscribers"""
        if run_id in websocket_connections:
            disconnected = []
            for connection in websocket_connections[run_id]:
                try:
                    await connection.send_json(update)
                except Exception:
                    disconnected.append(connection)
            
            for conn in disconnected:
                if conn in websocket_connections[run_id]:
                    websocket_connections[run_id].remove(conn)


manager = ConnectionManager()


# ============== WebSocket Endpoint ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time pipeline updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
            message = json.loads(data)
            if message.get("type") == "subscribe"):
                run_id = message.get("run_id")
                if run_id:
                    if run_id not in websocket_connections:
                        websocket_connections[run_id] = []
                    websocket_connections[run_id].append(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============== API Endpoints ==============

@app.get("/")
async def root():
    return {"message": "DevOps AI Command Center API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    """Check system health"""
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "region": os.environ.get("NODE_REGION", "US-EAST-1")
    }


@app.get("/api/status", response_model=dict)
async def get_system_status():
    """Get current system status"""
    return {
        "status": "Autonomous Agent Active",
        "active_nodes": 142,
        "uptime": 99.99,
        "region": os.environ.get("NODE_REGION", "US-EAST-1")
    }


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    # Calculate stats from pipeline runs
    total_runs = len(pipeline_runs)
    running_runs = sum(1 for r in pipeline_runs.values() if r.get("status") == "RUNNING")
    completed_runs = sum(1 for r in pipeline_runs.values() if r.get("status") == "COMPLETED")
    failed_runs = sum(1 for r in pipeline_runs.values() if r.get("status") == "FAILED")
    
    return {
        "active_deployments": running_runs,
        "ai_confidence": 98.4,
        "error_rate": 0.02,
        "infra_cost": 2450,
        "success_rate": (completed_runs / total_runs * 100) if total_runs > 0 else 100,
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "failed_runs": failed_runs
    }


@app.post("/api/runs", response_model=RunResponse)
async def create_run(run_data: RunCreate, background_tasks: BackgroundTasks):
    """Create a new pipeline run"""
    run_id = str(uuid4())
    created_at = datetime.utcnow()
    
    # Initialize run
    pipeline_runs[run_id] = {
        "id": run_id,
        "repo_url": run_data.repo_url,
        "branch": run_data.branch,
        "team_id": run_data.team_id,
        "status": "PENDING",
        "progress": 0,
        "current_step": "Initializing pipeline...",
        "iteration": 0,
        "total_failures": 0,
        "total_fixes": 0,
        "iterations_used": 0,
        "score": 0.0,
        "total_time_seconds": 0,
        "created_at": created_at,
        "failures_detected": [],
        "fixes_applied": [],
    }
    pipeline_logs[run_id] = []
    
    # Add initial log
    log_msg = f"[{created_at.isoformat()}] Pipeline initialized for {run_data.repo_url}"
    pipeline_logs[run_id].append(log_msg)
    
    # Start pipeline in background
    background_tasks.add_task(run_pipeline, run_id, run_data.repo_url, run_data.branch)
    
    return RunResponse(
        id=run_id,
        repo_url=run_data.repo_url,
        branch=run_data.branch,
        status="PENDING",
        progress=0,
        current_step="Initializing pipeline...",
        total_failures=0,
        total_fixes=0,
        iterations_used=0,
        score=0.0,
        total_time_seconds=0,
        created_at=created_at,
        logs=pipeline_logs[run_id]
    )


@app.get("/api/runs", response_model=List[RunResponse])
async def get_runs(limit: int = 20):
    """Get all pipeline runs"""
    runs = list(pipeline_runs.values())
    runs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return [
        RunResponse(
            id=run["id"],
            repo_url=run["repo_url"],
            branch=run["branch"],
            status=run["status"],
            progress=run["progress"],
            current_step=run["current_step"],
            total_failures=run["total_failures"],
            total_fixes=run["total_fixes"],
            iterations_used=run["iterations_used"],
            score=run["score"],
            total_time_seconds=run["total_time_seconds"],
            created_at=run["created_at"],
            logs=pipeline_logs.get(run["id"], [])[-10:]
        )
        for run in runs[:limit]
    ]


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    """Get a specific run by ID"""
    if run_id not in pipeline_runs:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = pipeline_runs[run_id]
    return RunResponse(
        id=run["id"],
        repo_url=run["repo_url"],
        branch=run["branch"],
        status=run["status"],
        progress=run["progress"],
        current_step=run["current_step"],
        total_failures=run["total_failures"],
        total_fixes=run["total_fixes"],
        iterations_used=run["iterations_used"],
        score=run["score"],
        total_time_seconds=run["total_time_seconds"],
        created_at=run["created_at"],
        logs=pipeline_logs.get(run_id, [])
    )


@app.get("/api/runs/{run_id}/status")
async def get_pipeline_status(run_id: str):
    """Get pipeline status and logs"""
    if run_id not in pipeline_runs:
        return {
            "run_id": run_id,
            "status": "UNKNOWN",
            "progress": 0,
            "current_step": "No pipeline found",
            "logs": []
        }
    
    run = pipeline_runs[run_id]
    return {
        "run_id": run_id,
        "status": run["status"],
        "progress": run["progress"],
        "current_step": run["current_step"],
        "iteration": run.get("iteration", 0),
        "failures_detected": run.get("failures_detected", []),
        "fixes_applied": run.get("fixes_applied", []),
        "logs": pipeline_logs.get(run_id, [])
    }


# ============== Background Pipeline Execution ==============

async def run_pipeline(run_id: str, repo_url: str, branch: str):
    """Execute the CI/CD healing pipeline in background"""
    start_time = datetime.utcnow()
    
    try:
        # Update status to RUNNING
        pipeline_runs[run_id]["status"] = "RUNNING"
        
        # Simulate pipeline steps
        steps = [
            ("Cloning repository...", 10),
            ("Analyzing CI failures...", 25),
            ("Classifying bugs...", 40),
            ("Generating fixes...", 55),
            ("Validating fixes...", 70),
            ("Running tests...", 85),
            ("Committing changes...", 95),
            ("Finalizing...", 100),
        ]
        
        # Simulated failures for demo
        simulated_failures = [
            {"file": "src/app.py", "line": 42, "type": "SYNTAX", "message": "IndentationError"},
            {"file": "tests/test_api.py", "line": 15, "type": "LOGIC", "message": "Assertion failed"},
        ]
        
        simulated_fixes = [
            {"file": "src/app.py", "line": 42, "type": "SYNTAX", "fix": "Fixed indentation"},
            {"file": "tests/test_api.py", "line": 15, "type": "LOGIC", "fix": "Updated assertion"},
        ]
        
        for i, (step, progress) in enumerate(steps):
            # Update run state
            pipeline_runs[run_id]["progress"] = progress
            pipeline_runs[run_id]["current_step"] = step
            pipeline_runs[run_id]["iteration"] = i + 1
            
            # Add log
            log_msg = f"[{datetime.utcnow().isoformat()}] {step}"
            if run_id in pipeline_logs:
                pipeline_logs[run_id].append(log_msg)
            
            # Add failures in analysis step
            if i == 1 and simulated_failures:
                pipeline_runs[run_id]["failures_detected"] = simulated_failures
                pipeline_runs[run_id]["total_failures"] = len(simulated_failures)
            
            # Add fixes in generation step
            if i == 3 and simulated_fixes:
                pipeline_runs[run_id]["fixes_applied"] = simulated_fixes[:1]
                pipeline_runs[run_id]["total_fixes"] = 1
            
            # Send WebSocket update
            update = {
                "type": "pipeline_update",
                "run_id": run_id,
                "status": "RUNNING",
                "progress": progress,
                "current_step": step,
                "iteration": i + 1,
                "failures_detected": pipeline_runs[run_id].get("failures_detected", []),
                "fixes_applied": pipeline_runs[run_id].get("fixes_applied", []),
                "logs": pipeline_logs.get(run_id, [])[-5:]
            }
            await manager.send_to_run(run_id, update)
            
            # Simulate work
            await asyncio.sleep(1.5)
        
        # Calculate final stats
        end_time = datetime.utcnow()
        total_time = int((end_time - start_time).total_seconds())
        
        # Update final status
        pipeline_runs[run_id].update({
            "status": "COMPLETED",
            "progress": 100,
            "current_step": "Pipeline completed successfully",
            "iterations_used": len(steps),
            "score": 92.5,
            "total_time_seconds": total_time,
            "ci_status": "PASSED"
        })
        
        # Send final update
        final_update = {
            "type": "pipeline_complete",
            "run_id": run_id,
            "status": "COMPLETED",
            "progress": 100,
            "current_step": "Pipeline completed successfully",
            "score": 92.5,
            "total_time_seconds": total_time,
            "total_failures": 2,
            "total_fixes": 1,
            "iterations_used": len(steps),
            "ci_status": "PASSED"
        }
        await manager.send_to_run(run_id, final_update)
        
    except Exception as e:
        # Handle errors
        error_msg = f"Pipeline failed: {str(e)}"
        pipeline_runs[run_id]["status"] = "FAILED"
        pipeline_runs[run_id]["current_step"] = error_msg
        
        if run_id in pipeline_logs:
            pipeline_logs[run_id].append(f"[{datetime.utcnow().isoformat()}] ERROR: {error_msg}")
        
        # Send error update
        await manager.send_to_run(run_id, {
            "type": "pipeline_error",
            "run_id": run_id,
            "status": "FAILED",
            "error": error_msg
        })


@app.get("/api/actions")
async def get_recent_actions():
    """Get recent AI agent actions"""
    # Get recent runs for actions
    runs = sorted(pipeline_runs.values(), key=lambda x: x["created_at"], reverse=True)[:10]
    
    actions = []
    for run in runs:
        if run["status"] == "COMPLETED":
            action_type = "Auto-healed"
            status = "success"
        elif run["status"] == "FAILED":
            action_type = "Analysis Failed"
            status = "error"
        elif run["status"] == "RUNNING":
            action_type = "Running Pipeline"
            status = "running"
        else:
            action_type = "Pending"
            status = "pending"
        
        actions.append({
            "id": run["id"],
            "type": action_type,
            "description": f"Repository: {run['repo_url']} - {run.get('total_failures', 0)} failures, {run.get('total_fixes', 0)} fixes",
            "timestamp": run["created_at"].isoformat() if isinstance(run["created_at"], datetime) else run["created_at"],
            "status": status
        })
    
    # Add default demo actions if no runs
    if not actions:
        actions = [
            {"id": "1", "type": "Kubernetes Auto-scaled", "description": "Traffic spike detected in US-West cluster. Provisioned 4 additional nodes.", "timestamp": datetime.utcnow().isoformat(), "status": "success"},
            {"id": "2", "type": "Security Vulnerability Patched", "description": "Identified CVE-2024-5120 in base image.", "timestamp": datetime.utcnow().isoformat(), "status": "success"},
            {"id": "3", "type": "Node Health Remediation", "description": "Node i-0a2f1b unresponsive. Restarted successfully.", "timestamp": datetime.utcnow().isoformat(), "status": "success"}
        ]
    
    return actions


@app.get("/api/latency")
async def get_latency_stats():
    """Get latency distribution stats"""
    return {
        "regions": [
            {"name": "US-EAST-1", "latency": 12, "percentage": 85},
            {"name": "EU-WEST-1", "latency": 42, "percentage": 45},
            {"name": "AP-SOUTH-1", "latency": 68, "percentage": 30}
        ]
    }


# ============== Supabase Auth Endpoints ==============

@app.get("/api/user/profile")
async def get_user_profile():
    """Get user profile from Supabase"""
    if not supabase:
        return {"error": "Supabase not configured"}
    
    try:
        user = supabase.auth.get_user()
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        return {
            "id": user.user.id,
            "email": user.user.email,
            "created_at": user.user.created_at
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
