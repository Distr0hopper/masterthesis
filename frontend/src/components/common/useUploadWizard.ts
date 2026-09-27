import { useState } from 'react';

/**
 * Step state of an upload wizard (UploadStepper): the current step, and the furthest one
 * reached - steps up to that stay clickable in the stepper.
 */
export function useUploadWizard() {
  const [step, setStep] = useState(1);
  const [furthest, setFurthest] = useState(1);

  const goTo = (next: number) => {
    setStep(next);
    setFurthest((prev) => Math.max(prev, next));
  };

  /** A new source invalidates everything read from the old one - only step 1 is reachable again. */
  const backToSource = () => {
    setStep(1);
    setFurthest(1);
  };

  return { step, furthest, goTo, backToSource };
}
