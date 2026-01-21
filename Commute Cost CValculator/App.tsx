import React, { useState, useEffect, useCallback } from 'react';
import { 
  Calculator, 
  Car, 
  Fuel, 
  MapPin, 
  Search, 
  TrendingUp, 
  AlertCircle,
  Link as LinkIcon,
  Wrench,
  Coins,
  TrendingDown
} from 'lucide-react';
import { getCarConsumptionEstimate, getRouteEstimate, getRouteFromUrl } from './services/geminiService';
import { CarSpecs, RouteDetails, FuelSettings, OtherCosts, CalculationResult, DepreciationYear } from './types';
import ResultsChart from './components/ResultsChart';

const App: React.FC = () => {
  // --- State ---
  
  // Default values
  const [carSpecs, setCarSpecs] = useState<CarSpecs>({
    make: 'Škoda',
    model: 'Octavia 2.0 TDI',
    year: '2020',
    fuelType: 'Diesel',
    consumption: 5.2,
  });

  const [route, setRoute] = useState<RouteDetails>({
    distanceOneWayKm: 0,
    frequencyDaysPerMonth: 21, // Default approx 5 days/week
    isRoundTrip: true,
  });

  const [fuel, setFuel] = useState<FuelSettings>({
    pricePerLiter: 38.50, // Realistic CZK price
    currency: 'Kč', 
  });

  // Purchase Price State
  const [purchasePrice, setPurchasePrice] = useState<number>(450000);

  // Updated state for specific costs
  const [otherCosts, setOtherCosts] = useState<OtherCosts>({
    serviceIntervalKm: 15000,
    serviceCost: 5000, 
    tireChangeCostYearly: 1600, // 2x800 CZK
    unexpectedRepairsYearly: 3000,
    parkingYearly: 0,
    tollsYearly: 1500, // CZ Annual Vignette
    insuranceYearly: 8000,
  });

  const [results, setResults] = useState<CalculationResult>({
    monthlyDistance: 0,
    yearlyDistance: 0,
    monthlyTotalCost: 0,
    monthlyFuelCost: 0,
    yearlyFuelCost: 0,
    yearlyServiceCost: 0,
    yearlyTireCost: 0,
    yearlyUnexpectedCost: 0,
    yearlyParkingCost: 0,
    yearlyTollCost: 0,
    yearlyInsuranceCost: 0,
    yearlyTotalCost: 0,
    servicesPerYear: 0,
  });

  const [depreciationTable, setDepreciationTable] = useState<DepreciationYear[]>([]);

  const [aiLoading, setAiLoading] = useState(false);
  const [aiRouteLoading, setAiRouteLoading] = useState(false);
  const [routeInputA, setRouteInputA] = useState('');
  const [routeInputB, setRouteInputB] = useState('');
  const [mapsLink, setMapsLink] = useState('');

  // --- Logic ---

  const calculate = useCallback(() => {
    const dailyDistance = route.distanceOneWayKm * (route.isRoundTrip ? 2 : 1);
    const monthlyDist = dailyDistance * route.frequencyDaysPerMonth;
    const yearlyDist = monthlyDist * 12;

    // 1. Fuel Costs
    const yearlyFuelNeeded = (yearlyDist / 100) * carSpecs.consumption;
    const costFuelYearly = yearlyFuelNeeded * fuel.pricePerLiter;

    // 2. Service Costs (Interval based)
    const servicesCount = yearlyDist / (otherCosts.serviceIntervalKm || 15000);
    const costServiceYearly = servicesCount * otherCosts.serviceCost;

    // 3. Fixed/Yearly Costs
    const costTiresYearly = otherCosts.tireChangeCostYearly;
    const costUnexpectedYearly = otherCosts.unexpectedRepairsYearly;
    const costParkingYearly = otherCosts.parkingYearly;
    const costTollsYearly = otherCosts.tollsYearly;
    const costInsuranceYearly = otherCosts.insuranceYearly;

    // Totals
    const totalYearly = costFuelYearly + costServiceYearly + costTiresYearly + costUnexpectedYearly + costParkingYearly + costTollsYearly + costInsuranceYearly;
    const totalMonthly = totalYearly / 12;
    const monthlyFuel = costFuelYearly / 12;

    setResults({
      monthlyDistance: monthlyDist,
      yearlyDistance: yearlyDist,
      monthlyTotalCost: totalMonthly,
      monthlyFuelCost: monthlyFuel,
      yearlyFuelCost: costFuelYearly,
      yearlyServiceCost: costServiceYearly,
      yearlyTireCost: costTiresYearly,
      yearlyUnexpectedCost: costUnexpectedYearly,
      yearlyParkingCost: costParkingYearly,
      yearlyTollCost: costTollsYearly,
      yearlyInsuranceCost: costInsuranceYearly,
      yearlyTotalCost: totalYearly,
      servicesPerYear: servicesCount
    });

    // 4. Advanced Depreciation Algorithm
    const table: DepreciationYear[] = [];
    let currentValue = purchasePrice;
    
    // Constants for the model
    const standardAnnualKm = 15000;
    
    for (let year = 1; year <= 5; year++) {
      const prevValue = currentValue;
      
      // A. Base Market Rate (Time Decay)
      // Used cars typically lose ~12-15% annually just by aging (rust, older tech).
      // We slightly decrease this rate over time (older cars stabilize).
      // Year 1: 14%, Year 5: 12%
      const baseTimeRate = 0.14 - (year * 0.005); 
      
      // B. Mileage Intensity Factor (Wear Decay)
      // How much harder is the car working than average?
      // Power of 0.6 creates a realistic curve (2x mileage != 2x depreciation, closer to 1.5x)
      const usageRatio = yearlyDist / standardAnnualKm;
      const mileageFactor = Math.pow(usageRatio, 0.6); 
      
      // Composition: We assume depreciation is roughly 60% Time-based and 40% Mileage-based.
      const timeComponent = baseTimeRate * 0.60;
      const wearComponent = (baseTimeRate * 0.40) * mileageFactor;
      
      const totalDecayRate = timeComponent + wearComponent;
      
      // Cap at reasonable max/min (e.g., car won't lose 80% in a year, nor 0%)
      const effectiveRate = Math.max(0.05, Math.min(0.40, totalDecayRate));
      
      currentValue = currentValue * (1 - effectiveRate);
      
      table.push({
        year,
        value: currentValue,
        lossTotal: purchasePrice - currentValue,
        lossYearly: prevValue - currentValue
      });
    }
    setDepreciationTable(table);

  }, [carSpecs.consumption, route, fuel.pricePerLiter, otherCosts, purchasePrice]);

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

  const handleUrlRouteEstimate = async () => {
    if (!mapsLink) return;
    setAiRouteLoading(true);
    const result = await getRouteFromUrl(mapsLink);
    if (result) {
      if (result.distanceKm) setRoute(prev => ({ ...prev, distanceOneWayKm: result.distanceKm }));
      if (result.start) setRouteInputA(result.start);
      if (result.end) setRouteInputB(result.end);
    }
    setAiRouteLoading(false);
  };

  const setFrequencyByDaysPerWeek = (daysPerWeek: number) => {
    const monthly = Math.round((daysPerWeek * 52) / 12);
    setRoute(prev => ({ ...prev, frequencyDaysPerMonth: monthly }));
  };

  // --- Render ---

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-12">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-2 rounded-lg text-white shadow-blue-200 shadow-lg">
              <Calculator size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">Kalkulačka Dochádzania</h1>
              <p className="text-xs text-slate-500 font-medium">Smart Commute Cost</p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs font-semibold bg-slate-100 px-3 py-1.5 rounded-full text-slate-600">
             <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
             Powered by Gemini AI
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Inputs */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Section 1: Route */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
              <MapPin className="text-red-500" size={20} />
              <h2 className="font-semibold text-slate-800">Trasa a Vzdialenosť</h2>
            </div>
            <div className="p-6 space-y-6">
              
              {/* Maps Link Input */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-100 relative overflow-hidden">
                 <div className="absolute top-0 right-0 p-4 opacity-5">
                    <LinkIcon size={80} />
                 </div>
                 <label className="block text-xs font-bold text-blue-800 uppercase mb-2 flex items-center gap-2">
                    <LinkIcon size={14} />
                    Import z Google Mapy
                 </label>
                 <div className="flex gap-2 relative z-10">
                    <input 
                      type="text" 
                      placeholder="Vložte odkaz (https://maps.app.goo.gl/...)" 
                      className="flex-1 bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none shadow-sm"
                      value={mapsLink}
                      onChange={(e) => setMapsLink(e.target.value)}
                    />
                    <button 
                      onClick={handleUrlRouteEstimate}
                      disabled={aiRouteLoading || !mapsLink}
                      className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-all shadow-md shadow-blue-200 flex items-center gap-2 whitespace-nowrap"
                    >
                      {aiRouteLoading ? 'Analyzujem...' : 'Načítať trasu'}
                    </button>
                 </div>
                 <div className="mt-2 text-[10px] text-blue-800/60 font-medium px-1">
                   Tip: Pre najlepšiu presnosť použite "dlhý" odkaz z prehliadača (obsahuje /dir/...), krátke odkazy môžu byť nepresné.
                 </div>
              </div>

              <div className="flex items-center gap-4 py-2">
                <div className="h-px bg-slate-200 flex-1"></div>
                <span className="text-xs font-medium text-slate-400 uppercase">alebo manuálne</span>
                <div className="h-px bg-slate-200 flex-1"></div>
              </div>

              {/* Manual/City Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Odkiaľ</label>
                    <input 
                      type="text" 
                      placeholder="Mesto / Adresa" 
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                      value={routeInputA}
                      onChange={(e) => setRouteInputA(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Kam</label>
                    <div className="flex gap-2">
                      <input 
                        type="text" 
                        placeholder="Mesto / Adresa" 
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                        value={routeInputB}
                        onChange={(e) => setRouteInputB(e.target.value)}
                      />
                      <button 
                        onClick={handleAiRouteEstimate}
                        disabled={aiRouteLoading || !routeInputA || !routeInputB}
                        className="bg-slate-200 text-slate-600 px-3 rounded-lg hover:bg-slate-300 disabled:opacity-50"
                        title="Vypočítať vzdialenosť"
                      >
                        <Search size={16} />
                      </button>
                    </div>
                  </div>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  
                  {/* Distance & Toggle */}
                  <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Vzdialenosť (jedna cesta)</label>
                        <div className="relative">
                          <input 
                            type="number" 
                            value={route.distanceOneWayKm || ''}
                            onChange={(e) => setRoute(prev => ({ ...prev, distanceOneWayKm: parseFloat(e.target.value) || 0 }))}
                            className="w-full bg-white border border-slate-200 rounded-lg pl-3 pr-12 py-2 text-lg font-bold text-slate-900 focus:ring-2 focus:ring-blue-500 outline-none"
                          />
                          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium">km</div>
                        </div>
                    </div>
                    <button 
                      onClick={() => setRoute(prev => ({ ...prev, isRoundTrip: !prev.isRoundTrip }))}
                      className={`w-full py-2 px-4 rounded-lg border text-sm font-medium transition-all flex items-center justify-between ${route.isRoundTrip ? 'bg-green-50 border-green-200 text-green-700' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
                    >
                      <span className="text-xs opacity-70">Spiatočne?</span>
                      <span className="font-bold">{route.isRoundTrip ? 'ÁNO' : 'NIE'}</span>
                    </button>
                  </div>
                  
                  {/* Frequency Control */}
                  <div className="flex flex-col">
                     <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Frekvencia jázd</label>
                     <div className="relative mb-3">
                       <input 
                          type="number"
                          value={route.frequencyDaysPerMonth}
                          onChange={(e) => setRoute(prev => ({ ...prev, frequencyDaysPerMonth: parseInt(e.target.value) || 0 }))}
                          className="w-full bg-white border border-slate-200 rounded-lg pl-3 pr-10 py-2 text-lg font-bold text-slate-900 focus:ring-2 focus:ring-blue-500 outline-none"
                       />
                       <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">dní/mes</span>
                    </div>
                    
                    {/* Quick Week Select */}
                    <div className="mt-auto">
                        <label className="block text-[10px] font-semibold text-slate-400 uppercase mb-1">Dni v týždni (rýchla voľba):</label>
                        <div className="flex justify-between gap-1">
                            {[1, 2, 3, 4, 5].map(days => (
                                <button
                                    key={days}
                                    onClick={() => setFrequencyByDaysPerWeek(days)}
                                    className={`flex-1 py-1.5 text-xs font-medium rounded border transition-colors
                                        ${Math.round((days * 52) / 12) === route.frequencyDaysPerMonth 
                                            ? 'bg-blue-100 border-blue-300 text-blue-700' 
                                            : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                                        }`}
                                >
                                    {days}x
                                </button>
                            ))}
                        </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </section>

          {/* Section 2: Vehicle */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
              <Car className="text-blue-600" size={20} />
              <h2 className="font-semibold text-slate-800">Vozidlo a Spotreba</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="col-span-1">
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Značka</label>
                  <input 
                    type="text" 
                    value={carSpecs.make}
                    onChange={(e) => setCarSpecs({...carSpecs, make: e.target.value})}
                    placeholder="Napr. Škoda"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Model</label>
                  <input 
                    type="text" 
                    value={carSpecs.model}
                    onChange={(e) => setCarSpecs({...carSpecs, model: e.target.value})}
                    placeholder="Napr. Octavia"
                    className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                <div className="col-span-1 sm:col-span-2">
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
              </div>
            </div>
          </section>

          {/* Section 3: Costs (Fuel & Service) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Fuel Costs */}
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
               <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
                <Fuel className="text-orange-500" size={20} />
                <h2 className="font-semibold text-slate-800">Cena Paliva</h2>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-1">Cena za liter</label>
                  <div className="flex gap-2">
                    <input 
                      type="number" 
                      step="0.01"
                      value={fuel.pricePerLiter}
                      onChange={(e) => setFuel(prev => ({ ...prev, pricePerLiter: parseFloat(e.target.value) || 0 }))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-lg font-bold text-slate-900 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                    <select 
                      value={fuel.currency}
                      onChange={(e) => setFuel(prev => ({ ...prev, currency: e.target.value }))}
                      className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 font-medium focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      <option value="€">€</option>
                      <option value="Kč">Kč</option>
                      <option value="$">$</option>
                    </select>
                  </div>
                </div>
              </div>
            </section>

            {/* Other Costs - REDESIGNED GRID */}
            <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
               <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
                <Wrench className="text-slate-600" size={20} />
                <h2 className="font-semibold text-slate-800">Servis a Poplatky</h2>
              </div>
              <div className="p-6">
                
                {/* 2-column Grid with consistent spacing */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-5">
                  
                  {/* Row 1: Service */}
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase mb-1">Servisný Interval</label>
                    <div className="relative">
                       <input 
                        type="number" 
                        value={otherCosts.serviceIntervalKm}
                        onChange={(e) => setOtherCosts(prev => ({ ...prev, serviceIntervalKm: parseInt(e.target.value) || 0 }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-2 text-sm font-bold text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                      <span className="absolute right-2 top-2 text-slate-400 text-xs">km</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase mb-1">Cena Prehliadky</label>
                    <div className="relative">
                      <input 
                        type="number" 
                        value={otherCosts.serviceCost}
                        onChange={(e) => setOtherCosts(prev => ({ ...prev, serviceCost: parseFloat(e.target.value) || 0 }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-bold text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none"
                      />
                    </div>
                  </div>

                  {/* Row 2: Tires & Repairs */}
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase mb-1" title="Cena za prezutie pneu 2x ročne">Prezutie Pneu (Rok)</label>
                    <input 
                      type="number" 
                      value={otherCosts.tireChangeCostYearly}
                      onChange={(e) => setOtherCosts(prev => ({ ...prev, tireChangeCostYearly: parseFloat(e.target.value) || 0 }))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase mb-1" title="Rozpočet na nečakané opravy">Nečakané Opravy (Rok)</label>
                    <input 
                      type="number" 
                      value={otherCosts.unexpectedRepairsYearly}
                      onChange={(e) => setOtherCosts(prev => ({ ...prev, unexpectedRepairsYearly: parseFloat(e.target.value) || 0 }))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>

                  {/* Row 3: Insurance (Full Width visually via col-span-2) */}
                  <div className="sm:col-span-2">
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase mb-1">Ročné Poistenie (PZP + Havarijné)</label>
                    <input 
                      type="number" 
                      value={otherCosts.insuranceYearly}
                      onChange={(e) => setOtherCosts(prev => ({ ...prev, insuranceYearly: parseFloat(e.target.value) || 0 }))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-bold text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>

                  {/* Row 4: Parking & Tolls */}
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase mb-1">Parkovanie (Rok)</label>
                    <input 
                      type="number" 
                      value={otherCosts.parkingYearly}
                      onChange={(e) => setOtherCosts(prev => ({ ...prev, parkingYearly: parseFloat(e.target.value) || 0 }))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase mb-1">Diaľničná Známka (Rok)</label>
                    <input 
                      type="number" 
                      value={otherCosts.tollsYearly}
                      onChange={(e) => setOtherCosts(prev => ({ ...prev, tollsYearly: parseFloat(e.target.value) || 0 }))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                  </div>

                </div>
              </div>
            </section>
          </div>

          {/* New Section: Valuation & Depreciation */}
          <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden lg:col-span-12">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
              <TrendingDown className="text-purple-600" size={20} />
              <h2 className="font-semibold text-slate-800">Strata Hodnoty Vozidla (Odhady)</h2>
            </div>
            <div className="p-6">
              <div className="flex flex-col md:flex-row gap-8">
                
                {/* Input */}
                <div className="md:w-1/3 space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">Kúpna Cena Vozidla</label>
                    <div className="relative">
                      <input 
                        type="number" 
                        value={purchasePrice}
                        onChange={(e) => setPurchasePrice(parseFloat(e.target.value) || 0)}
                        className="w-full bg-white border border-slate-200 rounded-lg pl-3 pr-10 py-3 text-xl font-bold text-slate-900 focus:ring-2 focus:ring-purple-500 outline-none shadow-sm"
                      />
                       <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 font-medium">{fuel.currency}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                      Kalkulácia počíta s trhovou stratou hodnoty zohľadňujúcou vek a váš nadpriemerný ročný nájazd.
                    </p>
                  </div>
                </div>

                {/* Table */}
                <div className="md:w-2/3 overflow-x-auto">
                   <table className="w-full text-sm text-left">
                     <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold">
                       <tr>
                         <th className="px-4 py-3 rounded-l-lg">Obdobie</th>
                         <th className="px-4 py-3">Odhadovaná Cena</th>
                         <th className="px-4 py-3">Strata (Ročne)</th>
                         <th className="px-4 py-3 rounded-r-lg">Strata (Celkom)</th>
                       </tr>
                     </thead>
                     <tbody className="divide-y divide-slate-100">
                       {depreciationTable.map((row) => (
                         <tr key={row.year} className="hover:bg-slate-50 transition-colors">
                           <td className="px-4 py-3 font-medium text-slate-700">O {row.year} {row.year === 1 ? 'rok' : (row.year > 1 && row.year < 5) ? 'roky' : 'rokov'}</td>
                           <td className="px-4 py-3 font-bold text-slate-900">{row.value.toLocaleString(undefined, {maximumFractionDigits:0})} {fuel.currency}</td>
                           <td className="px-4 py-3 text-red-500">-{row.lossYearly.toLocaleString(undefined, {maximumFractionDigits:0})} {fuel.currency}</td>
                           <td className="px-4 py-3 text-slate-400">-{row.lossTotal.toLocaleString(undefined, {maximumFractionDigits:0})} {fuel.currency}</td>
                         </tr>
                       ))}
                     </tbody>
                   </table>
                </div>

              </div>
            </div>
          </section>

        </div>

        {/* Right Column: Results */}
        <div className="lg:col-span-5 space-y-6">
          <div className="sticky top-24 space-y-6">
            
            {/* Main Result Card */}
            <div className="bg-slate-900 rounded-2xl shadow-xl text-white overflow-hidden p-6 relative group">
              <div className="absolute -right-6 -top-6 text-slate-800 opacity-20 group-hover:opacity-30 transition-opacity">
                <Coins size={140} />
              </div>
              
              <div className="relative z-10">
                <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Celkové Mesačné Náklady</h3>
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-5xl font-bold tracking-tight">
                    {results.monthlyTotalCost.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                  </span>
                  <span className="text-2xl text-slate-400 font-medium">{fuel.currency}</span>
                </div>
                <div className="text-sm text-slate-400 mb-6 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-orange-400"></span>
                  Palivo: {results.monthlyFuelCost.toFixed(0)} {fuel.currency}
                  <span className="mx-1">•</span>
                  <span className="w-2 h-2 rounded-full bg-slate-600"></span>
                  Ostatné: {(results.monthlyTotalCost - results.monthlyFuelCost).toFixed(0)} {fuel.currency}
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-white/10 pt-4">
                  <div>
                    <div className="text-slate-400 text-xs mb-1">Ročné celkové</div>
                    <div className="text-lg font-semibold text-white">
                      {results.yearlyTotalCost.toLocaleString(undefined, { maximumFractionDigits: 0 })} {fuel.currency}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 text-xs mb-1">Cena za 1 km</div>
                    <div className="text-lg font-semibold text-emerald-400">
                      {(results.monthlyTotalCost / (results.monthlyDistance || 1)).toFixed(2)} {fuel.currency}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Detailed Yearly Breakdown */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
                <TrendingUp size={18} className="text-blue-600"/>
                Detail Ročných Nákladov
              </h3>
              
              <div className="space-y-3">
                
                <div className="flex justify-between items-center text-sm">
                   <span className="text-slate-500 flex items-center gap-2">
                     <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                     Palivo (Ročne)
                   </span>
                   <span className="font-bold text-slate-700">{results.yearlyFuelCost.toLocaleString()} {fuel.currency}</span>
                </div>

                <div className="flex justify-between items-center text-sm">
                   <div className="flex flex-col">
                     <span className="text-slate-500 flex items-center gap-2">
                        <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                        Servisné prehliadky
                     </span>
                     <span className="text-[10px] text-slate-400 pl-4">
                       Interval {otherCosts.serviceIntervalKm.toLocaleString()} km ({results.servicesPerYear.toFixed(1)}x ročne)
                     </span>
                   </div>
                   <span className="font-bold text-slate-700">{results.yearlyServiceCost.toLocaleString(undefined, {maximumFractionDigits:0})} {fuel.currency}</span>
                </div>

                <div className="flex justify-between items-center text-sm">
                   <span className="text-slate-500 flex items-center gap-2">
                     <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                     Pneu a Opravy
                   </span>
                   <span className="font-bold text-slate-700">{(results.yearlyTireCost + results.yearlyUnexpectedCost).toLocaleString()} {fuel.currency}</span>
                </div>

                <div className="flex justify-between items-center text-sm border-b border-slate-100 pb-3">
                   <span className="text-slate-500 flex items-center gap-2">
                     <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                     Poplatky a Poistenie
                   </span>
                   <span className="font-bold text-slate-700">{(results.yearlyParkingCost + results.yearlyTollCost + results.yearlyInsuranceCost).toLocaleString()} {fuel.currency}</span>
                </div>

                 <div className="flex justify-between items-center py-2 bg-slate-50 px-3 rounded-lg mt-2">
                  <span className="text-slate-500 text-sm font-medium">Ročný Nájazd</span>
                  <span className="font-mono font-bold text-slate-900">{results.yearlyDistance.toLocaleString()} km</span>
                </div>
              </div>

              {/* Chart */}
              <div className="mt-4 pt-4 border-t border-slate-100">
                <ResultsChart results={results} currency={fuel.currency} />
              </div>
            </div>

            {/* Info Box - Updated per request */}
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex gap-3">
              <AlertCircle className="text-blue-600 flex-shrink-0 mt-0.5" size={24} />
              <div className="text-sm text-blue-900">
                <p className="font-bold mb-1 text-base">Servisný plán</p>
                <p className="opacity-80 leading-relaxed">
                  Pri ročnom nájazde {results.yearlyDistance.toLocaleString()} km a intervale {otherCosts.serviceIntervalKm.toLocaleString()} km absolvujete servisnú prehliadku priemerne <strong>{results.servicesPerYear.toFixed(1)}x ročne</strong>.
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