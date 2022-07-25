"""
Sentence Splitting Operator
Split Text
"""
from relevanceai.operations_new.ops_base import OperationAPIBase
from relevanceai.operations_new.processing.text.ner.transform import ExtractNER


class ExtractNEROps(OperationAPIBase, ExtractNER):
    def __init__(self, credentials, fields, output_fields, **kwargs):
        self.credentials = credentials
        if output_fields is None:
            self.output_fields = [self._generate_output_field(f) for f in fields]
        else:
            self.output_fields = output_fields
        for k, v in kwargs.items():
            setattr(self, k, v)
