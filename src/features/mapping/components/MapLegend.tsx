export function MapLegend() {
  return (
    <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-md p-4 z-[1000]">
      <h3 className="text-sm font-semibold text-neutral-900 mb-3">Property Class</h3>
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-blue-600" />
          <span className="text-sm text-neutral-700">Class A</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-green-600" />
          <span className="text-sm text-neutral-700">Class B</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-orange-600" />
          <span className="text-sm text-neutral-700">Class C</span>
        </div>
      </div>
    </div>
  );
}
