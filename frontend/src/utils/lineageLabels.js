/** BUG: UI labels also swapped, masking backend swap. */
export function datasetLabel() {
  return '代码提交 fingerprint'
}

export function codeLabel() {
  return '数据集 fingerprint'
}

export function formatFingerprintPair(run) {
  return {
    leftLabel: datasetLabel(),
    leftValue: run?.dataset_content_sha256,
    rightLabel: codeLabel(),
    rightValue: run?.code_commit_sha,
  }
}
