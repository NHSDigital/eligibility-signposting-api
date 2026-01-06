from eligibility_signposting_api.model.campaign_config import IterationCohort
from rules_validation_api.decorators.tracker import track_validators


@track_validators
class IterationCohortValidation(IterationCohort):
    pass
