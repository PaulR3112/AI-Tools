import React, { useState, useEffect, useCallback } from 'react';
import { 
  Calculator, 
  Car, 
  Fuel, 
  MapPin, 
  Calendar, 
  Search, 
  CheckCircle2, 
  TrendingUp, 
  AlertCircle 
} from 'lucide-react';
import { getCarConsumptionEstimate, getRouteEstimate } from './services/geminiService';
import { CarSpecs, RouteDetails, FuelSettings, CalculationResult } from './types';
import ResultsChart from './components/ResultsChart';

const App: React.FC = () => {
  // --- State ---
  
  // Default values based on user prompt: Toyota Hybrid 1.8 2023, 32.50 price, 10 days
  const [carSpecs, setCarSpecs] = useState<CarSpecs>({
    make: 'Toyota',
    model: 'Hybrid 1.8',
    year: '2023',
    fuelType: 'Benzín',
    consumption: 4.5, // Conservative estimate for Toyota Hybrid 1.8
  });

  const [route, setRoute] = useState<RouteDetails>({
    distanceOneWayKm: 0, // User needs to input this or AI finds it
    frequencyDaysPerMonth: 10,
    isRoundTrip: true,
  });

  const [fuel, setFuel] = useState<FuelSettings>({
    pricePerLiter: 32.50,
    currency: 'Kč', // Assuming CZK based on value 32.50, user can change
  });

  const [results, setResults] = useState<CalculationResult>({
    monthlyDistance: 0,
    monthlyFuelNeeded: 0,
    monthlyCost: 0,
    yearlyCost: 0,
    yearlyDistance: 0,
  });

  const [aiLoading, setAiLoading] = useState(false);
  const [aiRouteLoading, setAiRouteLoading] = useState(false);
  const [routeInputA, setRouteInputA] = useState('');
  const [routeInputB, setRouteInputB] = useState('');

  // --- Logic ---

  const calculate = useCallback(() => {
    const dailyDistance = route.distanceOneWayKm * (route.isRoundTrip ? 2 : 1);
    const monthlyDist = dailyDistance * route.frequencyDaysPerMonth;
    const yearlyDist = monthlyDist * 12; // Simple 12 month projection

    const fuelNeededMonthly = (monthlyDist / 100) * carSpecs.consumption;
    const costMonthly = fuelNeededMonthly * fuel.pricePerLiter;
    const costYearly = costMonthly * 12;

    setResults({
      monthlyDistance: monthlyDist,
      monthlyFuelNeeded: fuelNeededMonthly,
      monthlyCost: costMonthly,
      yearlyCost: costYearly,
      yearlyDistance: yearlyDist,
    });
  }, [carSpecs.consumption, route, fuel.pricePerLiter]);

  useEffect(() => {
    calculate();
  }, [calculate]);

  // --- Handlers ---

  const handleAiCarEstimate = async () => {
    if (!carSpecs.make && !carSpecs.model) return;
    setAiLoading(true);
    const query = `${carSpecs.year} ${carSpecs.make} ${carSpecs.model} ${carSpecs.fuelType}`;
    const estimate = await getCarConsumptionEstimate(query);
    if (estimate) {
      setCarSpecs(prev => ({
        ...prev,
        consumption: estimate.consumption,
        make: estimate.make || prev.make,
        model: estimate.model || prev.model
      }));
    }
    setAiLoading(false);
  };

  const handleAiRouteEstimate = async () => {
    if (!routeInputA || !routeInputB) return;
    setAiRouteLoading(true);
    const result = await getRouteEstimate(routeInputA, routeInputB);
    if (result && result.distanceKm) {
      setRoute(prev => ({ ...prev, distanceOneWayKm: result.distanceKm }));
    }
    setAiRouteLoading(false);
  };

  // --- Render ---

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-12">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-2 rounded-lg text-white">
              <Calculator size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">Kalkulačka Dochádzania</h1>
              <p className="text-xs text-slate-500">Toyota Hybrid 1.8 (2023) Edition</p>
            </div>
          </div>
          <div className="hidden sm:block text-sm text-slate-500 font-medium">
            Powered by Gemini AI
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Inputs */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Section 1: Vehicle */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
              <Car className="text-blue-600" size={20} />
              <h2 className="font-semibold text-slate-800">Vozidlo a Spotreba</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Značka / Model</label>
                  <input 
                    type="text" 
                    value={`${carSpecs.make} ${carSpecs.model}`}
                    onChange={(e) => {
                      const parts = e.target.value.split(' ');
                      setCarSpecs({...carSpecs, make: parts[0] || '', model: parts.slice(1).join(' ') || ''});
                    }}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Rok Výroby</label>
                  <input 
                    type="text" 
                    value={carSpecs.year}
                    onChange={(e) => setCarSpecs({...carSpecs, year: e.target.value})}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-semibold text-slate-500 uppercase">
                    Spotreba (l/100km)
                  </label>
                  <button 
                    onClick={handleAiCarEstimate}
                    disabled={aiLoading}
                    className="text-xs text-blue-600 font-medium hover:text-blue-700 flex items-center gap-1 disabled:opacity-50"
                  >
                    {aiLoading ? 'Zisťujem...' : (
                      <>
                        <Search size={12} />
                        AI Odhad
                      </>
                    )}
                  </button>
                </div>
                <div className="flex items-center gap-3">
                  <input 
                    type="range" 
                    min="2" 
                    max="15" 
                    step="0.1"
                    value={carSpecs.consumption}
                    onChange={(e) => setCarSpecs({...carSpecs, consumption: parseFloat(e.target.value)})}
                    className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <div className="w-20 text-right font-mono font-bold text-slate-700">
                    {carSpecs.consumption.toFixed(1)} l
                  </div>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  Toyota Hybrid 1.8 má zvyčajne spotrebu medzi 4.2 - 5.0 l/100km v závislosti od štýlu jazdy.
                </p>
              </div>
            </div>
          </section>

          {/* Section 2: Route */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
              <MapPin className="text-red-500" size={20} />
              <h2 className="font-semibold text-slate-800">Trasa a Vzdialenosť</h2>
            </div>
            <div className="p-6 space-y-6">
              
              <div className="bg-blue-50/50 rounded-lg p-4 border border-blue-100">
                <label className="block text-xs font-semibold text-blue-800 uppercase mb-2">
                  AI Výpočet vzdialenosti
                </label>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input 
                    type="text" 
                    placeholder="Odkiaľ (Mesto/Ulica)" 
                    className="flex-1 bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={routeInputA}
                    onChange={(e) => setRouteInputA(e.target.value)}
                  />
                  <input 
                    type="text" 
                    placeholder="Kam" 
                    className="flex-1 bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={routeInputB}
                    onChange={(e) => setRouteInputB(e.target.value)}
                  />
                  <button 
                    onClick={handleAiRouteEstimate}
                    disabled={aiRouteLoading || !routeInputA || !routeInputB}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                  >
                    {aiRouteLoading ? '...' : <Search size={16} />}
                    <span className="sm:hidden">Hľadať</span>
                  </button>
                </div>
                <p className="text-xs text-blue-600/70 mt-2">
                  Zadajte mestá (napr. "Bratislava" a "Trnava") a AI zistí vzdialenosť.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Vzdialenosť (jedna cesta)</label>
                <div className="relative">
                  <input 
                    type="number" 
                    value={route.distanceOneWayKm || ''}
                    placeholder="Zadajte km ak viete presne"
                    onChange={(e) => setRoute(prev => ({ ...prev, distanceOneWayKm: parseFloat(e.target.value) || 0 }))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-12 py-3 text-lg font-semibold focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium">km</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                 <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Cesta tam aj späť?</label>
                    <button 
                      onClick={() => setRoute(prev => ({ ...prev, isRoundTrip: !prev.isRoundTrip }))}
                      className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-sm font-medium transition-all ${route.isRoundTrip ? 'bg-green-50 border-green-200 text-green-700' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
                    >
                      {route.isRoundTrip ? <CheckCircle2 size={16} /> : <div className="w-4 h-4 rounded-full border-2 border-slate-300" />}
                      {route.isRoundTrip ? 'Áno (2x)' : 'Nie (1x)'}
                    </button>
                 </div>
                 <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Dni v mesiaci</label>
                    <div className="relative flex items-center">
                       <Calendar className="absolute left-3 text-slate-400" size={16} />
                       <input 
                          type="number"
                          value={route.frequencyDaysPerMonth}
                          onChange={(e) => setRoute(prev => ({ ...prev, frequencyDaysPerMonth: parseInt(e.target.value) || 0 }))}
                          className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-10 pr-3 py-2 text-sm font-semibold focus:ring-2 focus:ring-blue-500 outline-none"
                       />
                    </div>
                 </div>
              </div>
            </div>
          </section>

          {/* Section 3: Price */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
             <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
              <Fuel className="text-orange-500" size={20} />
              <h2 className="font-semibold text-slate-800">Cena Paliva</h2>
            </div>
            <div className="p-6 grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Cena za liter</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={fuel.pricePerLiter}
                  onChange={(e) => setFuel(prev => ({ ...prev, pricePerLiter: parseFloat(e.target.value) || 0 }))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-lg font-semibold focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Mena</label>
                <select 
                  value={fuel.currency}
                  onChange={(e) => setFuel(prev => ({ ...prev, currency: e.target.value }))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm font-medium focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer"
                >
                  <option value="Kč">CZK (Kč)</option>
                  <option value="€">EUR (€)</option>
                  <option value="$">USD ($)</option>
                </select>
              </div>
            </div>
          </section>

        </div>

        {/* Right Column: Results */}
        <div className="lg:col-span-5 space-y-6">
          <div className="sticky top-24 space-y-6">
            
            {/* Main Result Card */}
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl shadow-xl text-white overflow-hidden p-6 relative">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <TrendingUp size={100} />
              </div>
              
              <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Mesačné Náklady</h3>
              <div className="flex items-baseline gap-2 mb-6">
                <span className="text-5xl font-bold tracking-tight">
                  {results.monthlyCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="text-2xl text-slate-400 font-medium">{fuel.currency}</span>
              </div>

              <div className="grid grid-cols-2 gap-4 border-t border-white/10 pt-4">
                <div>
                  <div className="text-slate-400 text-xs mb-1">Ročné náklady</div>
                  <div className="text-xl font-semibold">
                    {results.yearlyCost.toLocaleString(undefined, { maximumFractionDigits: 0 })} {fuel.currency}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 text-xs mb-1">Spotrebované palivo</div>
                  <div className="text-xl font-semibold text-orange-400">
                    {results.monthlyFuelNeeded.toFixed(1)} L
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Breakdown */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-800 mb-4">Prehľad Jazdy</h3>
              
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-slate-500 text-sm">Vzdialenosť (mesiac)</span>
                  <span className="font-mono font-medium text-slate-900">{results.monthlyDistance.toLocaleString()} km</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-slate-500 text-sm">Vzdialenosť (rok)</span>
                  <span className="font-mono font-medium text-slate-900">{results.yearlyDistance.toLocaleString()} km</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-slate-100">
                  <span className="text-slate-500 text-sm">Cena za 1 km</span>
                  <span className="font-mono font-medium text-slate-900">
                    {((carSpecs.consumption / 100) * fuel.pricePerLiter).toFixed(2)} {fuel.currency}
                  </span>
                </div>
              </div>

              {/* Chart */}
              <div className="mt-6 pt-4 border-t border-slate-100">
                <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">Porovnanie nákladov</h4>
                <ResultsChart results={results} currency={fuel.currency} />
              </div>
            </div>

            {/* Info Box */}
            <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 flex gap-3">
              <AlertCircle className="text-emerald-600 flex-shrink-0" size={20} />
              <div className="text-sm text-emerald-800">
                <p className="font-medium mb-1">Ekologická jazda</p>
                <p className="opacity-80">
                  Toyota Hybrid 1.8 je vysoko efektívna v meste. Skutočná spotreba môže byť nižšia ako 4.5l/100km ak využívate rekuperáciu.
                </p>
              </div>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
};

export default App;