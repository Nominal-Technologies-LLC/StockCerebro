interface Props {
  active: string;
  onChange: (tf: string) => void;
}

const timeframes = [
  { id: 'h', label: 'Hourly' },
  { id: 'd', label: 'Daily' },
  { id: 'w', label: 'Weekly' },
];

export default function TimeframeSelector({ active, onChange }: Props) {
  return (
    <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
      {timeframes.map((tf) => (
        <button
          key={tf.id}
          onClick={() => onChange(tf.id)}
          className={`px-3 py-1 text-sm rounded-md transition-colors ${
            active === tf.id
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          {tf.label}
        </button>
      ))}
    </div>
  );
}
