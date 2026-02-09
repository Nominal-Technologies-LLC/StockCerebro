import { getGradeColor, getGradeBgColor } from '../../utils/grading';

interface Props {
  grade: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function LetterGrade({ grade, size = 'md' }: Props) {
  const textColor = getGradeColor(grade);

  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-10 h-10 text-lg',
    lg: 'w-14 h-14 text-2xl',
  };

  const gradientMap: Record<string, string> = {
    'A': 'bg-gradient-to-br from-green-500/30 to-green-600/15 border-green-500/50 shadow-green-500/15',
    'B': 'bg-gradient-to-br from-emerald-500/30 to-emerald-600/15 border-emerald-500/50 shadow-emerald-500/15',
    'C': 'bg-gradient-to-br from-yellow-500/35 to-yellow-600/15 border-yellow-500/50 shadow-yellow-500/15',
    'D': 'bg-gradient-to-br from-orange-500/35 to-orange-600/15 border-orange-500/50 shadow-orange-500/15',
    'F': 'bg-gradient-to-br from-red-500/35 to-red-600/15 border-red-500/50 shadow-red-500/15',
  };

  const gradeLetter = grade[0];
  const gradient = gradientMap[gradeLetter] || 'bg-gradient-to-br from-gray-500/30 to-gray-600/15 border-gray-500/50 shadow-gray-500/15';

  return (
    <div
      className={`
        ${sizeClasses[size]}
        ${textColor}
        ${gradient}
        rounded-lg border-2
        shadow-md
        flex items-center justify-center font-bold
        transition-all duration-300 hover:scale-105
      `}
    >
      {grade}
    </div>
  );
}
