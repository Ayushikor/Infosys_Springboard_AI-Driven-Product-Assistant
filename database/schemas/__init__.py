"""Document structures and validators for the collections the backend uses."""

from . import (
    activity_schema,
    analysis_batch_schema,
    analysis_run_schema,
    chat_schema,
    feature_schema,
    feedback_schema,
    prd_schema,
    product_schema,
    roadmap_schema,
    theme_schema,
    user_schema,
    user_state_schema,
    workspace_schema,
)

from .activity_schema import validate_activity
from .analysis_batch_schema import validate_analysis_batch
from .analysis_run_schema import validate_analysis_run
from .chat_schema import validate_chat_message
from .feature_schema import validate_feature
from .feedback_schema import validate_feedback
from .prd_schema import validate_prd
from .product_schema import validate_product
from .roadmap_schema import validate_roadmap
from .theme_schema import validate_theme
from .user_schema import validate_user
from .user_state_schema import validate_user_state
from .workspace_schema import validate_workspace


SCHEMA_MODULES = [
    user_schema,
    workspace_schema,
    user_state_schema,
    product_schema,
    feedback_schema,
    theme_schema,
    feature_schema,
    prd_schema,
    roadmap_schema,
    chat_schema,
    activity_schema,
    analysis_run_schema,
    analysis_batch_schema,
]


VALIDATORS = {
    user_schema.COLLECTION: validate_user,
    workspace_schema.COLLECTION: validate_workspace,
    user_state_schema.COLLECTION: validate_user_state,
    product_schema.COLLECTION: validate_product,
    feedback_schema.COLLECTION: validate_feedback,
    theme_schema.COLLECTION: validate_theme,
    feature_schema.COLLECTION: validate_feature,
    prd_schema.COLLECTION: validate_prd,
    roadmap_schema.COLLECTION: validate_roadmap,
    chat_schema.COLLECTION: validate_chat_message,
    activity_schema.COLLECTION: validate_activity,
    analysis_run_schema.COLLECTION: validate_analysis_run,
    analysis_batch_schema.COLLECTION: validate_analysis_batch,
}

def validate(collection, doc):
    """Validate a document against its collection schema."""
    return VALIDATORS[collection](doc)