// Pattern cn() di shadcn/ui e Agent Elements (entrambi MIT):
// https://github.com/21st-dev/agent-elements — clsx + tailwind-merge.
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
