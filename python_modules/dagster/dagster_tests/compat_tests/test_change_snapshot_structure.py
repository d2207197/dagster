from dagster.core.instance import DagsterInstance, InstanceRef
from dagster.core.snap import (
    ExecutionPlanIndex,
    PipelineIndex,
    create_execution_plan_snapshot_id,
    create_pipeline_snapshot_id,
)
from dagster.utils import file_relative_path
from dagster.utils.test import restore_directory


# a change of schema in the snapshot hierarchy caused hashes to be different
# when snapshots reloaded
def test_0_7_10_snapshot_id_change():
    test_dir = file_relative_path(__file__, 'snapshot_0_7_9_shapshot_id_creation_change/sqlite')
    with restore_directory(test_dir):

        instance = DagsterInstance.from_ref(InstanceRef.from_dir(test_dir))
        # run_id = 'e297fa70-49e8-43f8-abfe-1634f02644f6'

        old_pipeline_snapshot_id = '88528edde2ed64da3c39cca0da8ba2f7586c1a5d'
        old_execution_plan_snapshot_id = '2246f8e5a10d21e15fbfa3773d7b2d0bc1fa9d3d'

        pipeline_snapshot = instance.get_pipeline_snapshot(old_pipeline_snapshot_id)
        ep_snapshot = instance.get_execution_plan_snapshot(old_execution_plan_snapshot_id)

        # It is the pipeline snapshot that changed
        # Verify that snapshot ids are not equal
        assert create_pipeline_snapshot_id(pipeline_snapshot) != old_pipeline_snapshot_id

        assert create_execution_plan_snapshot_id(ep_snapshot) == old_execution_plan_snapshot_id

        # This previously failed with a check error
        assert ExecutionPlanIndex(ep_snapshot, PipelineIndex(pipeline_snapshot))


# Scripts to create this (run against 0.7.9)
#
# from dagster import pipeline, solid, DagsterInstance, execute_pipeline
# from dagster.core.snap.utils import create_snapshot_id
#
# from dagster.serdes import serialize_pp
#
# @solid
# def noop_solid(_):
#     pass
#
# @pipeline
# def noop_pipeline():
#     noop_solid()
#
# instance = DagsterInstance.get()
#
# result = execute_pipeline(noop_pipeline, instance=instance)
#
# run_id = result.run_id

# print(serialize_pp(run))