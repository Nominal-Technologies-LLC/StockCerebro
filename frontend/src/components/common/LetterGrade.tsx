import { getGradeColor, getGradeBgColor } from '../../utils/grading';

interface Props {
  grade: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function LetterGrade({ grade, size = 'md' }: Props) {
  const textColor = getGradeColor(grade);
  const bgColor = getGradeBgColor(grade);

  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-10 h-10 text-lg',
    lg: 'w-14 h-14 text-2xl',
  };

  return (
    <div
      className={`${sizeClasses[size]} ${textColor} ${bgColor} rounded-lg border flex items-center justify-center font-bold`}
    >
      {grade}
    </div>
  );
}
