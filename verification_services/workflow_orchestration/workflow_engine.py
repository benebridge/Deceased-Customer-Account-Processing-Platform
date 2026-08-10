"""
Workflow Engine
Implements Chapter 5 dynamic workflow generation and execution

Generates account-type specific workflows and orchestrates parallel verification tasks
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import VerificationResult, VerificationStatus


class TaskStatus(Enum):
    """Workflow task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"  # Must complete
    HIGH = "high"  # Should complete
    MEDIUM = "medium"  # Important but optional
    LOW = "low"  # Nice to have


@dataclass
class WorkflowTask:
    """
    Individual verification task in a workflow
    """
    task_id: str
    task_type: str  # 'death_cert_blockchain', 'id_verification', 'fraud_detection', etc.
    description: str
    priority: TaskPriority
    dependencies: List[str] = field(default_factory=list)  # Task IDs that must complete first
    parallel_group: Optional[str] = None  # Tasks in same group run in parallel
    timeout_seconds: int = 120

    # Execution state
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[VerificationResult] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'description': self.description,
            'priority': self.priority.value,
            'dependencies': self.dependencies,
            'parallel_group': self.parallel_group,
            'status': self.status.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message
        }


@dataclass
class Workflow:
    """
    Complete verification workflow for a case
    """
    workflow_id: str
    case_id: str
    account_type: str
    tasks: List[WorkflowTask]
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # SLA tracking
    sla_deadline: Optional[datetime] = None
    escalation_level: int = 0

    def get_task(self, task_id: str) -> Optional[WorkflowTask]:
        """Get task by ID"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_ready_tasks(self) -> List[WorkflowTask]:
        """Get tasks ready to execute (dependencies met)"""
        ready = []
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are completed
            deps_met = True
            for dep_id in task.dependencies:
                dep_task = self.get_task(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    deps_met = False
                    break

            if deps_met:
                ready.append(task)

        return ready

    def get_progress(self) -> Dict:
        """Get workflow progress statistics"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
        in_progress = sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)

        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress,
            'pending': pending,
            'percentage': (completed / total * 100) if total > 0 else 0
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'workflow_id': self.workflow_id,
            'case_id': self.case_id,
            'account_type': self.account_type,
            'tasks': [t.to_dict() for t in self.tasks],
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'sla_deadline': self.sla_deadline.isoformat() if self.sla_deadline else None,
            'escalation_level': self.escalation_level,
            'progress': self.get_progress()
        }


class WorkflowEngine:
    """
    Dynamic workflow generation and execution engine

    Per Chapter 5:
    - Generates account-type specific workflows
    - Executes tasks in parallel where possible
    - Manages dependencies between tasks
    - Tracks SLA and escalations
    - Provides real-time progress updates
    """

    def __init__(self, max_parallel_tasks: int = 5):
        """
        Initialize workflow engine

        Args:
            max_parallel_tasks: Maximum number of tasks to run in parallel
        """
        self.max_parallel_tasks = max_parallel_tasks
        self.active_workflows: Dict[str, Workflow] = {}

        # Task executor for parallel execution
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_tasks)

        # Workflow templates by account type
        self.workflow_templates = self._initialize_workflow_templates()

    def generate_workflow(
        self,
        case_id: str,
        account_type: str,
        account_balance: float,
        state: str,
        has_blockchain_cert: bool = False
    ) -> Workflow:
        """
        Generate dynamic workflow based on case characteristics

        Per Chapter 5:
        - Different account types require different verifications
        - High-value accounts get enhanced verification
        - California cases can use blockchain verification
        - Workflows are optimized for parallel execution

        Args:
            case_id: Unique case identifier
            account_type: Type of account (checking, savings, ira, life_insurance, etc.)
            account_balance: Account value
            state: State where deceased resided
            has_blockchain_cert: Whether death certificate has blockchain seal

        Returns:
            Generated Workflow with all tasks
        """
        workflow_id = f"WF-{case_id}-{int(time.time())}"

        # Get base template for account type
        template_name = self._get_template_name(account_type, account_balance)
        template = self.workflow_templates.get(template_name, self.workflow_templates['standard'])

        tasks = []

        # STEP 1: Death Certificate Verification (always required)
        if has_blockchain_cert and state == 'CA':
            # Use blockchain verification (faster, more reliable)
            tasks.append(WorkflowTask(
                task_id='death_cert_blockchain',
                task_type='death_cert_verification_blockchain',
                description='Verify death certificate via Titan Seal blockchain',
                priority=TaskPriority.CRITICAL,
                dependencies=[],
                parallel_group='initial',
                timeout_seconds=30
            ))
        else:
            # Use traditional verification
            tasks.append(WorkflowTask(
                task_id='death_cert_traditional',
                task_type='death_cert_verification_traditional',
                description='Verify death certificate via computer vision and SSDI',
                priority=TaskPriority.CRITICAL,
                dependencies=[],
                parallel_group='initial',
                timeout_seconds=120
            ))

        # STEP 2: ID Verification (can run in parallel with death cert)
        tasks.append(WorkflowTask(
            task_id='id_document_verification',
            task_type='id_verification_document',
            description='Verify beneficiary government-issued ID',
            priority=TaskPriority.CRITICAL,
            dependencies=[],
            parallel_group='initial',
            timeout_seconds=90
        ))

        tasks.append(WorkflowTask(
            task_id='facial_recognition',
            task_type='id_verification_facial',
            description='Verify beneficiary face matches ID photo',
            priority=TaskPriority.HIGH,
            dependencies=['id_document_verification'],
            timeout_seconds=60
        ))

        # STEP 3: Fraud Detection (runs after initial verifications)
        death_cert_dep = 'death_cert_blockchain' if has_blockchain_cert and state == 'CA' else 'death_cert_traditional'

        tasks.append(WorkflowTask(
            task_id='fraud_rules',
            task_type='fraud_detection_rules',
            description='Rule-based fraud detection',
            priority=TaskPriority.CRITICAL,
            dependencies=[death_cert_dep, 'id_document_verification'],
            parallel_group='fraud_detection',
            timeout_seconds=30
        ))

        tasks.append(WorkflowTask(
            task_id='fraud_ml',
            task_type='fraud_detection_ml',
            description='ML-based anomaly detection',
            priority=TaskPriority.HIGH,
            dependencies=[death_cert_dep, 'id_document_verification'],
            parallel_group='fraud_detection',
            timeout_seconds=45
        ))

        # STEP 4: Enhanced verification for high-value accounts
        if account_balance > 100000:
            tasks.append(WorkflowTask(
                task_id='enhanced_background_check',
                task_type='enhanced_verification',
                description='Enhanced background and beneficiary verification',
                priority=TaskPriority.HIGH,
                dependencies=['fraud_rules'],
                timeout_seconds=180
            ))

            tasks.append(WorkflowTask(
                task_id='multi_angle_facial',
                task_type='id_verification_multi_angle',
                description='Multi-angle facial verification',
                priority=TaskPriority.MEDIUM,
                dependencies=['facial_recognition'],
                timeout_seconds=90
            ))

        # STEP 5: Account-specific verifications
        if account_type == 'ira' or account_type == '401k':
            # Retirement accounts need beneficiary designation verification
            tasks.append(WorkflowTask(
                task_id='beneficiary_designation_check',
                task_type='beneficiary_verification',
                description='Verify beneficiary designation on file',
                priority=TaskPriority.CRITICAL,
                dependencies=[death_cert_dep],
                timeout_seconds=60
            ))

        if account_type == 'life_insurance':
            # Life insurance needs additional policy verification
            tasks.append(WorkflowTask(
                task_id='policy_verification',
                task_type='policy_verification',
                description='Verify life insurance policy status and coverage',
                priority=TaskPriority.CRITICAL,
                dependencies=[death_cert_dep],
                timeout_seconds=90
            ))

        if account_type == 'trust':
            # Trust accounts need trust document verification
            tasks.append(WorkflowTask(
                task_id='trust_document_verification',
                task_type='trust_verification',
                description='Verify trust documents and trustee authority',
                priority=TaskPriority.CRITICAL,
                dependencies=[death_cert_dep, 'id_document_verification'],
                timeout_seconds=180
            ))

        # STEP 6: Final compliance check (depends on all critical tasks)
        critical_task_ids = [t.task_id for t in tasks if t.priority == TaskPriority.CRITICAL]
        tasks.append(WorkflowTask(
            task_id='final_compliance_check',
            task_type='compliance_verification',
            description='Final regulatory compliance verification',
            priority=TaskPriority.CRITICAL,
            dependencies=critical_task_ids,
            timeout_seconds=60
        ))

        workflow = Workflow(
            workflow_id=workflow_id,
            case_id=case_id,
            account_type=account_type,
            tasks=tasks
        )

        # Set SLA deadline based on account type and value
        workflow.sla_deadline = self._calculate_sla_deadline(account_type, account_balance)

        # Register workflow
        self.active_workflows[workflow_id] = workflow

        return workflow

    def execute_workflow(
        self,
        workflow: Workflow,
        task_executor_func: callable
    ) -> Dict:
        """
        Execute workflow with parallel task execution

        Args:
            workflow: Workflow to execute
            task_executor_func: Function to execute individual tasks
                                Signature: func(task: WorkflowTask) -> VerificationResult

        Returns:
            Execution summary with results
        """
        start_time = time.time()

        while True:
            # Get tasks ready to execute
            ready_tasks = workflow.get_ready_tasks()

            if not ready_tasks:
                # Check if workflow is complete
                progress = workflow.get_progress()
                if progress['pending'] == 0 and progress['in_progress'] == 0:
                    break

                # No ready tasks but work pending - wait for dependencies
                time.sleep(0.1)
                continue

            # Group tasks by parallel_group
            parallel_groups = {}
            for task in ready_tasks:
                group = task.parallel_group or task.task_id
                if group not in parallel_groups:
                    parallel_groups[group] = []
                parallel_groups[group].append(task)

            # Execute each parallel group
            for group_name, group_tasks in parallel_groups.items():
                futures = {}

                # Submit tasks for parallel execution
                for task in group_tasks:
                    task.status = TaskStatus.IN_PROGRESS
                    task.start_time = datetime.now()

                    future = self.executor.submit(
                        self._execute_task_with_timeout,
                        task,
                        task_executor_func
                    )
                    futures[future] = task

                # Wait for completion
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        task.end_time = datetime.now()
                    except Exception as e:
                        task.status = TaskStatus.FAILED
                        task.error_message = str(e)
                        task.end_time = datetime.now()

                        # If critical task fails, might need to abort workflow
                        if task.priority == TaskPriority.CRITICAL:
                            print(f"Critical task {task.task_id} failed: {e}")

        workflow.completed_at = datetime.now()
        execution_time = (time.time() - start_time) * 1000

        # Generate execution summary
        progress = workflow.get_progress()

        # Determine overall workflow status
        critical_tasks = [t for t in workflow.tasks if t.priority == TaskPriority.CRITICAL]
        critical_failed = any(t.status == TaskStatus.FAILED for t in critical_tasks)

        if critical_failed:
            overall_status = 'failed'
        elif progress['failed'] > 0:
            overall_status = 'partial_success'
        else:
            overall_status = 'success'

        return {
            'workflow_id': workflow.workflow_id,
            'case_id': workflow.case_id,
            'status': overall_status,
            'execution_time_ms': execution_time,
            'progress': progress,
            'tasks': [t.to_dict() for t in workflow.tasks],
            'completed_at': workflow.completed_at.isoformat()
        }

    def _execute_task_with_timeout(
        self,
        task: WorkflowTask,
        executor_func: callable
    ) -> VerificationResult:
        """Execute task with timeout handling"""
        try:
            result = executor_func(task)
            return result
        except TimeoutError:
            raise Exception(f"Task {task.task_id} timed out after {task.timeout_seconds}s")
        except Exception as e:
            raise Exception(f"Task {task.task_id} execution error: {str(e)}")

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get real-time workflow status"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return None

        return workflow.to_dict()

    def _get_template_name(self, account_type: str, account_balance: float) -> str:
        """Determine workflow template based on account characteristics"""
        if account_balance > 500000:
            return 'high_value'
        elif account_type in ['trust', 'estate']:
            return 'trust_estate'
        elif account_type in ['ira', '401k', 'pension']:
            return 'retirement'
        elif account_type == 'life_insurance':
            return 'life_insurance'
        else:
            return 'standard'

    def _calculate_sla_deadline(self, account_type: str, account_balance: float) -> datetime:
        """Calculate SLA deadline based on case characteristics"""
        from datetime import timedelta

        # Base SLA: 48 hours for standard cases
        base_hours = 48

        # High-value cases get priority (24 hours)
        if account_balance > 500000:
            base_hours = 24

        # Complex account types need more time
        if account_type in ['trust', 'estate']:
            base_hours = 72

        return datetime.now() + timedelta(hours=base_hours)

    def _initialize_workflow_templates(self) -> Dict[str, Dict]:
        """Initialize workflow templates for different account types"""
        return {
            'standard': {
                'name': 'Standard Verification',
                'description': 'Standard workflow for checking/savings accounts',
                'base_tasks': ['death_cert', 'id_verification', 'fraud_detection']
            },
            'high_value': {
                'name': 'High-Value Account Verification',
                'description': 'Enhanced verification for accounts >$500k',
                'base_tasks': ['death_cert', 'id_verification', 'fraud_detection', 'enhanced_verification']
            },
            'retirement': {
                'name': 'Retirement Account Verification',
                'description': 'Workflow for IRA, 401k, pension accounts',
                'base_tasks': ['death_cert', 'id_verification', 'beneficiary_designation', 'fraud_detection']
            },
            'life_insurance': {
                'name': 'Life Insurance Policy Verification',
                'description': 'Workflow for life insurance claims',
                'base_tasks': ['death_cert', 'id_verification', 'policy_verification', 'fraud_detection']
            },
            'trust_estate': {
                'name': 'Trust/Estate Account Verification',
                'description': 'Complex workflow for trust and estate accounts',
                'base_tasks': ['death_cert', 'id_verification', 'trust_verification', 'fraud_detection']
            }
        }
