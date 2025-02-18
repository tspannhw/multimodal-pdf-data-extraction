# SPDX-FileCopyrightText: Copyright (c) 2024, NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: Apache-2.0


# pylint: disable=too-few-public-methods
# pylint: disable=too-many-arguments

import logging
import os
from typing import Dict
from typing import Literal
from typing import get_args

from pydantic import BaseModel
from pydantic import root_validator
from pydantic import validator

from .task_base import Task

logger = logging.getLogger(__name__)

ECLAIR_TRITON_HOST = os.environ.get("ECLAIR_TRITON_HOST", "localhost")
ECLAIR_TRITON_PORT = os.environ.get("ECLAIR_TRITON_PORT", "8001")
ECLAIR_BATCH_SIZE = os.environ.get("ECLAIR_TRITON_PORT", "16")

UNSTRUCTURED_API_KEY = os.environ.get("UNSTRUCTURED_API_KEY", None)
UNSTRUCTURED_URL = os.environ.get("UNSTRUCTURED_URL", "https://api.unstructured.io/general/v0/general")
UNSTRUCTURED_STRATEGY = os.environ.get("UNSTRUCTURED_STRATEGY", "auto")
UNSTRUCTURED_CONCURRENCY_LEVEL = os.environ.get("UNSTRUCTURED_CONCURRENCY_LEVEL", 10)

ADOBE_CLIENT_ID = os.environ.get("ADOBE_CLIENT_ID", None)
ADOBE_CLIENT_SECRET = os.environ.get("ADOBE_CLIENT_SECRET", None)

_DEFAULT_EXTRACTOR_MAP = {
    "pdf": "pdfium",
    "docx": "python_docx",
    "pptx": "python_pptx",
    "html": "beautifulsoup",
    "xml": "lxml",
    "excel": "openpyxl",
    "csv": "pandas",
    "parquet": "pandas",
}

_Type_Extract_Method_PDF = Literal[
    "pdfium",
    "eclair",
    "haystack",
    "tika",
    "unstructured_io",
    "llama_parse",
    "adobe",
]

_Type_Extract_Method_DOCX = Literal["python_docx", "haystack", "unstructured_local", "unstructured_service"]

_Type_Extract_Method_PPTX = Literal["python_pptx", "haystack", "unstructured_local", "unstructured_service"]

_Type_Extract_Method_Map = {
    "pdf": get_args(_Type_Extract_Method_PDF),
    "docx": get_args(_Type_Extract_Method_DOCX),
    "pptx": get_args(_Type_Extract_Method_PPTX),
}

_Type_Extract_Tables_Method_PDF = Literal["yolox", "pdfium"]

_Type_Extract_Tables_Method_DOCX = Literal["python_docx",]

_Type_Extract_Tables_Method_PPTX = Literal["python_pptx",]

_Type_Extract_Tables_Method_Map = {
    "pdf": get_args(_Type_Extract_Tables_Method_PDF),
    "docx": get_args(_Type_Extract_Tables_Method_DOCX),
    "pptx": get_args(_Type_Extract_Tables_Method_PPTX),
}


class ExtractTaskSchema(BaseModel):
    document_type: str
    extract_method: str = None  # Initially allow None to set a smart default
    extract_text: bool = (True,)
    extract_images: bool = (True,)
    extract_tables: bool = False
    extract_tables_method: str = "yolox"
    text_depth: str = "document"

    @root_validator(pre=True)
    def set_default_extract_method(cls, values):
        document_type = values.get("document_type", "").lower()  # Ensure case-insensitive comparison
        extract_method = values.get("extract_method")

        if document_type not in _DEFAULT_EXTRACTOR_MAP:
            raise ValueError(
                f"Unsupported document type: {document_type}."
                f" Supported types are: {list(_DEFAULT_EXTRACTOR_MAP.keys())}"
            )

        if extract_method is None:
            values["extract_method"] = _DEFAULT_EXTRACTOR_MAP[document_type]
        return values

    @validator("extract_method")
    def extract_method_must_be_valid(cls, v, values, **kwargs):
        document_type = values.get("document_type", "").lower()  # Ensure case-insensitive comparison
        valid_methods = set(_Type_Extract_Method_Map[document_type])
        if v not in valid_methods:
            raise ValueError(f"extract_method must be one of {valid_methods}")
        return v

    @validator("document_type")
    def document_type_must_be_supported(cls, v):
        if v.lower() not in _DEFAULT_EXTRACTOR_MAP:
            raise ValueError(
                f"Unsupported document type '{v}'. Supported types are: {', '.join(_DEFAULT_EXTRACTOR_MAP.keys())}"
            )
        return v.lower()

    @validator("extract_tables_method")
    def extract_tables_method_must_be_valid(cls, v, values, **kwargs):
        document_type = values.get("document_type", "").lower()  # Ensure case-insensitive comparison
        valid_methods = set(_Type_Extract_Tables_Method_Map[document_type])
        if v not in valid_methods:
            raise ValueError(f"extract_method must be one of {valid_methods}")
        return v

    class Config:
        extra = "forbid"


class ExtractTask(Task):
    """
    Object for document extraction task
    """

    def __init__(
        self,
        document_type,
        extract_method: _Type_Extract_Method_PDF = "pdfium",
        extract_text: bool = False,
        extract_images: bool = False,
        extract_tables: bool = False,
        extract_tables_method: _Type_Extract_Tables_Method_PDF = "yolox",
        text_depth: str = "document",
    ) -> None:
        """
        Setup Extract Task Config
        """
        super().__init__()

        self._document_type = document_type
        self._extract_images = extract_images
        self._extract_method = extract_method
        self._extract_tables = extract_tables
        self._extract_tables_method = extract_tables_method
        self._extract_text = extract_text
        self._text_depth = text_depth

    def __str__(self) -> str:
        """
        Returns a string with the object's config and run time state
        """
        info = ""
        info += "Extract Task:\n"
        info += f"  document type: {self._document_type}\n"
        info += f"  extract method: {self._extract_method}\n"
        info += f"  extract text: {self._extract_text}\n"
        info += f"  extract images: {self._extract_images}\n"
        info += f"  extract tables: {self._extract_tables}\n"
        info += f"  extract tables method: {self._extract_tables_method}\n"
        info += f"  text depth: {self._text_depth}\n"
        return info

    def to_dict(self) -> Dict:
        """
        Convert to a dict for submission to redis (fixme)
        """
        extract_params = {
            "extract_text": self._extract_text,
            "extract_images": self._extract_images,
            "extract_tables": self._extract_tables,
            "extract_tables_method": self._extract_tables_method,
            "text_depth": self._text_depth,
        }

        task_properties = {
            "method": self._extract_method,
            "document_type": self._document_type,
            "params": extract_params,
        }

        # TODO(Devin): I like the idea of Derived classes augmenting the to_dict method, but its not logically
        #  consistent with how we define tasks, we don't have multiple extract tasks, we have extraction paths based on
        #  the method and the document type.
        if self._extract_method == "unstructured_local":
            unstructured_properties = {
                "api_key": "",  # TODO(Devin): Should be an environment variable or configurable parameter
                "unstructured_url": "",  # TODO(Devin): Should be an environment variable
            }
            task_properties["params"].update(unstructured_properties)
        elif self._extract_method == "eclair":
            eclair_properties = {
                "eclair_triton_host": os.environ.get("ECLAIR_TRITON_HOST", ECLAIR_TRITON_HOST),
                "eclair_triton_port": os.environ.get("ECLAIR_TRITON_PORT", ECLAIR_TRITON_PORT),
                "eclair_batch_size": os.environ.get("ECLAIR_BATCH_SIZE", ECLAIR_BATCH_SIZE),
            }
            task_properties["params"].update(eclair_properties)
        elif self._extract_method == "unstructured_io":
            unstructured_properties = {
                "unstructured_api_key": os.environ.get("UNSTRUCTURED_API_KEY", UNSTRUCTURED_API_KEY),
                "unstructured_url": os.environ.get("UNSTRUCTURED_URL", UNSTRUCTURED_URL),
                "unstructured_strategy": os.environ.get("UNSTRUCTURED_STRATEGY", UNSTRUCTURED_STRATEGY),
                "unstructured_concurrency_level": os.environ.get(
                    "UNSTRUCTURED_CONCURRENCY_LEVEL", UNSTRUCTURED_CONCURRENCY_LEVEL
                ),
            }
            task_properties["params"].update(unstructured_properties)
        elif self._extract_method == "adobe":
            adobe_properties = {
                "adobe_client_id": os.environ.get("ADOBE_CLIENT_ID", ADOBE_CLIENT_ID),
                "adobe_client_secrect": os.environ.get("ADOBE_CLIENT_SECRET", ADOBE_CLIENT_SECRET),
            }
            task_properties["params"].update(adobe_properties)
        return {"type": "extract", "task_properties": task_properties}
