from typing import List, Dict, Any, Optional

from relevanceai.dataset import Dataset
from relevanceai.operations_new.run import OperationRun


class OperationManager:
    """
    Operation manager manages an operation.
    It handles storing operation manager.

    In future, it will also handle:
    - logging
    - timing
    - Faster asynchronous processing
    - Have post-operation hooks (such as centroid insertion)
    """

    def __init__(
        self,
        dataset: Dataset,
        operation: OperationRun,
        metadata: Optional[Dict[str, Any]] = None,
        post_hooks: Optional[list] = None,
    ):
        self.dataset = dataset
        self.operation = operation
        self.metadata = metadata
        self.post_hooks = post_hooks if post_hooks is not None else []

    def __enter__(self):
        return self.dataset

    def __exit__(self, *args, **kwargs):
        from relevanceai.operations_new.cluster.ops import ClusterOps
        from relevanceai.operations_new.cluster.sub.ops import SubClusterOps

        if isinstance(self.operation, (ClusterOps, SubClusterOps)):
            # If we get here, the operetion must be clustering and we should upsert centroid docs
            centroid_documents = self.operation.get_centroid_documents()
            self.operation.insert_centroids(centroid_documents)

        for h in self.post_hooks:
            h()

        self.operation.store_operation_metadata(
            dataset=self.dataset,
            values=self.metadata,
        )

    @staticmethod
    def clean(
        before_docs: List[Dict[str, Any]],
        after_docs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        updated_documents = [
            {
                key: value
                for key, value in after_doc.items()
                if key not in before_doc or key == "_id"
            }
            for (before_doc, after_doc,) in zip(
                before_docs,
                after_docs,
            )
        ]
        return updated_documents
