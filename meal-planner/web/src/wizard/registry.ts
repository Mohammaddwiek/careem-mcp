import { portions, type Answers } from './answers'
import { StepAllergies, StepBudget, StepDays, StepDiet, StepDislikes, StepKitchen, StepMeals, StepPantry, StepVibe, StepWho } from './steps'

export const STEPS = [StepWho, StepMeals, StepDays, StepKitchen, StepDiet, StepVibe, StepAllergies, StepDislikes, StepPantry, StepBudget]

/** Why the user can't continue from a step yet (null when they can). */
export function blocker(step: number, a: Answers): string | null {
  if (step === 0 && portions(a) === 0) return 'Add at least one person.'
  if (step === 1 && a.meals.length === 0) return 'Pick at least one meal.'
  if (step === 2 && a.days.length === 0) return 'Pick at least one day.'
  if (step === 9 && a.budget < 50) return 'Set a budget of at least AED 50.'
  return null
}
