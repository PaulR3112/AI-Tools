import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { CalculationResult } from '../types';

interface ResultsChartProps {
  results: CalculationResult;
  currency: string;
}

const ResultsChart: React.FC<ResultsChartProps> = ({ results, currency }) => {
  const data = [
    {
      name: 'Ročné Náklady',
      Palivo: results.yearlyFuelCost,
      Servis: results.yearlyServiceCost,
      'Pneu/Opravy': results.yearlyTireCost + results.yearlyUnexpectedCost,
      Poplatky: results.yearlyParkingCost + results.yearlyTollCost + results.yearlyInsuranceCost
    }
  ];

  return (
    <div className="h-48 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
          <XAxis type="number" hide />
          <YAxis dataKey="name" type="category" width={100} tick={{fill: '#64748b', fontSize: 12, fontWeight: 500}} />
          <Tooltip 
            cursor={{fill: 'transparent'}}
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            formatter={(value: number) => `${value.toLocaleString(undefined, {maximumFractionDigits: 0})} ${currency}`}
          />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
          <Bar dataKey="Palivo" stackId="a" fill="#3b82f6" radius={[0, 0, 0, 0]} barSize={40} />
          <Bar dataKey="Servis" stackId="a" fill="#ef4444" radius={[0, 0, 0, 0]} barSize={40} />
          <Bar dataKey="Pneu/Opravy" stackId="a" fill="#f59e0b" radius={[0, 0, 0, 0]} barSize={40} />
          <Bar dataKey="Poplatky" stackId="a" fill="#a855f7" radius={[0, 4, 4, 0]} barSize={40} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ResultsChart;