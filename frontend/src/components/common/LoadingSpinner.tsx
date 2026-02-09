interface Props {
  message?: string;
}

export default function LoadingSpinner({ message = 'Loading...' }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-10 h-10 border-[3px] border-gray-700 border-t-blue-500 rounded-full animate-spin" />
      <p className="text-gray-500 mt-4 text-sm">{message}</p>
    </div>
  );
}
