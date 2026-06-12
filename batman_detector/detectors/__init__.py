from .bal_system_contract_index_confusion import BalSystemContractIndexConfusionDetector
from .bal_mixed_read_write_alias import BalMixedReadWriteAliasDetector


DETECTORS = {
    BalSystemContractIndexConfusionDetector.detector_id: BalSystemContractIndexConfusionDetector,
    BalMixedReadWriteAliasDetector.detector_id: BalMixedReadWriteAliasDetector,
}
