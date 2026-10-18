import { livenessAPI } from '../api/client';

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function livenessFailure(message) {
  const error = new Error(message);
  error.isLivenessFailure = true;
  return error;
}

/** Run the random blink/head-turn check using fresh webcam frames. */
export async function runLivenessChallenge(cameraRef, onInstruction = () => {}, groupMode = false) {
  const { data: challenge } = await livenessAPI.createChallenge(groupMode);
  const deadline = Date.now() + challenge.timeout_seconds * 1000;
  onInstruction(challenge.instruction);

  while (Date.now() < deadline) {
    const frame = cameraRef.current?.captureFrame();
    if (!frame) {
      await delay(300);
      continue;
    }

    const { data: result } = await livenessAPI.verify(challenge.challenge_id, frame);
    if (result.liveness === 'PASS') {
      return { challengeId: challenge.challenge_id, frameData: frame };
    }
    if (result.liveness === 'FAIL') {
      throw livenessFailure(result.message || 'Liveness check failed. Please try again.');
    }
    onInstruction(result.message || challenge.instruction);
    // Blinks are brief; sample again promptly so a natural closure is not
    // skipped between requests. API processing time still spaces the frames.
    await delay(120);
  }

  throw livenessFailure('Liveness check timed out. Please try again.');
}
