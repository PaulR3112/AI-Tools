import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { CalculationResult } from '../types';

interface ResultsChartProps {
  results: CalculationResult;
  currency: string;
}

const ResultsChart: React.FC<ResultsChartProps> = ({ results, currency }) => {
  const data = [
    {
      name: 'Mesačne',
      cost: results.monthlyCost,
      color: '#3b82f6'
    },
    {
      name: 'Ročne',
      cost: results.yearlyCost,
      color: '#10b981'
    }
  ];

  return (
    <div className="h-64 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
          <XAxis type="number" hide />
          <YAxis dataKey="name" type="category" width={80} tick={{fill: '#64748b'}} />
          <Tooltip 
            formatter={(value: number) => [`${value.toFixed(2)} ${currency}`, 'Náklady']}
            cursor={{fill: 'transparent'}}
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          <Bar dataKey="cost" radius={[0, 4, 4, 0]} barSize={40}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ResultsChart;