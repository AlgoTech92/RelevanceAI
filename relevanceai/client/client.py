"""Relevance AI's base Client class - primarily used to login and access the Dataset class or ClusterOps class.  The recomended way to log in is using: .. code-block:: from relevanceai import Client client = Client() client.list_datasets()
If the user already knows their project and API key, they can
log in this way:

.. code-block::

    from relevanceai import Client
    project = ""
    api_key = ""
    client = Client(project=project, api_key=api_key, firebase_uid=firebase_uid)
    client.list_datasets()

If you need to change your token, simply run:

.. code-block::

    from relevanceai import Client
    client = Client(token="...")

"""
import getpass
import pandas as pd
import analytics

from base64 import b64decode as decode
from typing import Dict, List, Optional, Union

from relevanceai._api import APIClient

from doc_utils.doc_utils import DocUtils

from relevanceai.client.helpers import *

from relevanceai.operations.cluster import ClusterOps
from relevanceai.operations.cluster.sub import SubClusterOps
from relevanceai.operations.viz import ClusterVizOps
from relevanceai.constants.errors import APIError
from relevanceai.constants.messages import Messages
from relevanceai.dataset import Dataset

from relevanceai.utils.decorators.analytics import track, identify
from relevanceai.utils.decorators.version import beta, added
from relevanceai.utils.config_mixin import ConfigMixin


class Client(APIClient, ConfigMixin):
    def __init__(
        self,
        token: Optional[str] = None,
        authenticate: bool = True,
    ):
        """
        Initialize the client

        Parameters
        -------------

        token: str
            You can paste the token here if things need to be refreshed

        force_refresh: bool
            If True, it forces you to refresh your client
        """

        if token is None:
            token = auth()

        self.token = token
        self.credentials = process_token(token)
        super().__init__(self.credentials)

        # Eventually the following should be accessed directly from
        # self.credentials, but keep for now.
        (
            self.project,
            self.api_key,
            self.region,
            self.firebase_uid,
        ) = self.credentials.split_token()

        self.base_url = region_to_url(self.region)
        self.base_ingest_url = region_to_url(self.region)

        try:
            self._set_mixpanel_write_key()
        except Exception as e:
            pass

        self._identify()

        # used to debug
        if authenticate:
            if self.check_auth():
                print(Messages.WELCOME_MESSAGE.format(self.project))
            else:
                raise APIError(Messages.FAIL_MESSAGE)

        # Add non breaking changes to support old ways of inserting documents and csv
        # self.insert_documents = Dataset(
        #     credentials=self.credentials,
        #     dataset_id="",
        # )._insert_documents
        # self.insert_csv = Dataset(
        #     credentials=self.credentials,
        #     dataset_id="",
        # )._insert_csv

    @identify
    def _identify(self):
        return

    def _set_mixpanel_write_key(self):
        analytics.write_key = decode(self.mixpanel_write_key).decode("utf-8")

    def _get_token(self):
        # TODO: either use cache or keyring package
        token = getpass.getpass(f"Activation token:")
        return token

    @property
    def auth_header(self):
        return {"Authorization": self.project + ":" + self.api_key}

    def make_search_suggestion(self):
        return self.services.search.make_suggestion()

    def check_auth(self):
        print(f"Connecting to {self.region}...")
        return self.list_datasets()

    @track
    def create_dataset(self, dataset_id: str, schema: Optional[Dict] = None):
        """
        A dataset can store documents to be searched, retrieved, filtered and aggregated (similar to Collections in MongoDB, Tables in SQL, Indexes in ElasticSearch).
        A powerful and core feature of VecDB is that you can store both your metadata and vectors in the same document. When specifying the schema of a dataset and inserting your own vector use the suffix (ends with) "_vector_" for the field name, and specify the length of the vector in dataset_schema. \n

        For example:

        .. code-block::
            {
                "product_image_vector_": 1024,
                "product_text_description_vector_" : 128
            }

        These are the field types supported in our datasets: ["text", "numeric", "date", "dict", "chunks", "vector", "chunkvector"]. \n

        For example:

        .. code-block::

            {
                "product_text_description" : "text",
                "price" : "numeric",
                "created_date" : "date",
                "product_texts_chunk_": "chunks",
                "product_text_chunkvector_" : 1024
            }

        You don't have to specify the schema of every single field when creating a dataset, as VecDB will automatically detect the appropriate data type for each field (vectors will be automatically identified by its "_vector_" suffix). Infact you also don't always have to use this endpoint to create a dataset as /datasets/bulk_insert will infer and create the dataset and schema as you insert new documents. \n

        Note:

            - A dataset name/id can only contain undercase letters, dash, underscore and numbers.
            - "_id" is reserved as the key and id of a document.
            - Once a schema is set for a dataset it cannot be altered. If it has to be altered, utlise the copy dataset endpoint.

        For more information about vectors check out the 'Vectorizing' section, services.search.vector or out blog at https://relevance.ai/blog. For more information about chunks and chunk vectors check out services.search.chunk.

        Parameters
        ----------
        dataset_id: str
            The unique name of your dataset
        schema : dict
            Schema for specifying the field that are vectors and its length

        Example
        ----------
        .. code-block::

            from relevanceai import Client
            client = Client()
            client.create_dataset("sample_dataset_id")

        """
        schema = {} if schema is None else schema
        return self.datasets.create(dataset_id, schema=schema)

    @track
    def list_datasets(self):
        """List Datasets

        Example
        ----------

        .. code-block::

            from relevanceai import Client
            client = Client()
            client.list_datasets()

        """
        self.print_dashboard_message(
            "You can view all your datasets at https://cloud.relevance.ai/datasets/"
        )
        datasets = self.datasets.list()
        datasets["datasets"] = sorted(datasets["datasets"])
        return datasets

    @track
    def delete_dataset(self, dataset_id):
        """
        Delete a dataset

        Parameters
        ------------
        dataset_id: str
            The ID of a dataset

        Example
        ---------

        .. code-block::

            from relevanceai import Client
            client = Client()
            client.delete_dataset("sample_dataset_id")

        """
        return self.datasets.delete(dataset_id)

    @track
    def Dataset(
        self,
        dataset_id: str,
        fields: Optional[List[str]] = None,
        image_fields: Optional[List[str]] = None,
        audio_fields: Optional[List[str]] = None,
        highlight_fields: Optional[Dict[str, List]] = None,
        text_fields: Optional[List[str]] = None,
    ):
        fields = [] if fields is None else fields
        image_fields = [] if image_fields is None else image_fields
        audio_fields = [] if audio_fields is None else audio_fields
        highlight_fields = {} if highlight_fields is None else highlight_fields
        text_fields = [] if text_fields is None else text_fields
        return Dataset(
            credentials=self.credentials,
            dataset_id=dataset_id,
            fields=fields,
            image_fields=image_fields,
            audio_fields=audio_fields,
            highlight_fields=highlight_fields,
            text_fields=text_fields,
        )

    ### Clustering

    @track
    def ClusterOps(
        self,
        model=None,
        **kwargs,
    ):
        return ClusterOps(
            credentials=self.credentials,
            model=model,
            **kwargs,
        )

    @track
    def ClusterVizOps(
        self,
        vector_fields: List[str],
        alias: str,
        dataset_id: str,
        **kwargs,
    ):
        return ClusterVizOps(
            credentials=self.credentials,
            vector_fields=vector_fields,
            alias=alias,
            dataset_id=dataset_id,
            **kwargs,
        )

    @track
    def SubClusterOps(
        self,
        credentials,
        alias,
        dataset,
        model,
        vector_fields: list,
        parent_field: str,
    ):
        """
        Sub Cluster Ops.
        """
        return SubClusterOps(
            credentials=self.credentials,
            alias=alias,
            dataset=dataset,
            model=model,
            vector_fields=vector_fields,
            parent_field=parent_field,
        )

    def _set_logger_to_verbose(self):
        # Use this for debugging
        self.config["logging.logging_level"] = "INFO"

    @track
    def send_dataset(
        self,
        dataset_id: str,
        receiver_project: str,
        receiver_api_key: str,
    ):
        """
        Send an individual a dataset. For this, you must know their API key.


        Parameters
        -----------

        dataset_id: str
            The name of the dataset
        receiver_project: str
            The project name that will receive the dataset
        receiver_api_key: str
            The project API key that will receive the dataset


        Example
        --------

        .. code-block::

            client = Client()
            client.send_dataset(
                dataset_id="research",
                receiver_project="...",
                receiver_api_key="..."
            )

        """
        return self.admin.send_dataset(
            dataset_id=dataset_id,
            receiver_project=receiver_project,
            receiver_api_key=receiver_api_key,
        )

    @track
    def receive_dataset(
        self,
        dataset_id: str,
        sender_project: str,
        sender_api_key: str,
    ):
        """
        Recieve an individual a dataset.

        Example
        --------
        >>> client = Client()
        >>> client.admin.receive_dataset(
            dataset_id="research",
            sender_project="...",
            sender_api_key="..."
        )

        Parameters
        -----------

        dataset_id: str
            The name of the dataset
        sender_project: str
            The project name that will send the dataset
        sender_api_key: str
            The project API key that will send the dataset

        """
        return self.admin.receive_dataset(
            dataset_id=dataset_id,
            sender_project=sender_project,
            sender_api_key=sender_api_key,
        )

    @track
    def clone_dataset(
        self,
        source_dataset_id: str,
        new_dataset_id: Optional[str] = None,
        source_project: Optional[str] = None,
        source_api_key: Optional[str] = None,
        project: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        # To do this should be cloning a dataset in a project
        """
        Clone a dataset from another user's projects into your project.

        Parameters
        ----------
        dataset_id:
            The dataset to copy
        source_dataset_id:
            The original dataset
        source_project:
            The original project to copy from
        source_api_key:
            The original API key of the project
        project:
            The original project
        api_key:
            The original API key

        Example
        -----------

        .. code-block::

            client = Client()
            client.clone_dataset(
                dataset_id="research",
                source_project="...",
                source_api_key="..."
            )

        """
        if source_api_key is None:
            source_api_key = self.api_key
            source_project = self.project

        if new_dataset_id is None:
            new_dataset_id = source_dataset_id

        return self.admin.copy_foreign_dataset(
            dataset_id=new_dataset_id,
            source_dataset_id=source_dataset_id,
            source_project=source_project,
            source_api_key=source_api_key,
            project=project,
            api_key=api_key,
        )

    @property
    def references(self):
        from relevanceai.__init__ import __version__

        REFERENCE_URL = f"https://relevanceai.readthedocs.io/en/{__version__}/"
        MESSAGE = f"You can find your references here {REFERENCE_URL}."
        print(MESSAGE)

    docs = references

    def search_app(self, dataset_id: Optional[str] = None):
        if dataset_id is not None:
            self.print_search_dashboard_url(dataset_id)
        elif hasattr(self, "_dataset_id"):
            self.print_search_dashboard_url(self._dataset_id)
        elif hasattr(self, "dataset_id"):
            self.print_search_dashboard_url(self.dataset_id)
        else:
            print("You can build your search app at https://cloud.relevance.ai")

    @added(version="1.1.3")
    @track
    def search_datasets(self, query: str):
        """
        Search through your datasets.
        """
        return [x for x in self.list_datasets()["datasets"] if query in x]

    @added(version="2.1.3")
    @beta
    def list_cluster_reports(self):
        """

        List all cluster reports.

        .. code-block::

            from relevanceai import Client
            client = Client()
            client.list_cluster_reports()

        """
        return pd.DataFrame(self.reports.clusters.list()["results"])

    @added(version="2.1.3")
    @beta
    @track
    def delete_cluster_report(self, cluster_report_id: str):
        """

        Delete Cluster Report

        .. code-block::

            from relevanceai import Client
            client = Client()
            client.delete_cluster_report("cluster_id_goes_here")

        """
        return self.reports.clusters.delete(cluster_report_id)

    @added(version="2.1.3")
    @beta
    @track
    def store_cluster_report(self, report_name: str, report: dict):
        """

        Store the cluster data.

        .. code-block::

            from relevanceai import Client
            client = Client()
            client.store_cluster_report("sample", {"value": 3})

        """
        response: dict = self.reports.clusters.create(
            name=report_name, report=self.json_encoder(report)
        )
        print(
            f"You can now access your report at https://cloud.relevance.ai/report/cluster/{self.region}/{response['_id']}"
        )
        return response

    def disable_analytics_tracking(self):
        """Disable analytics tracking if you would prefer not to send usage
        data to improve the product. Analytics allows us to improve your experience
        by examining the most popular flows, dedicating more resources to popular
        product features and improve user experience.
        """
        self.config["mixpanel.is_tracking_enabled"] = False