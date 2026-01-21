export interface CarSpecs {
  make: string;
  model: string;
  year: string;
  fuelType: string;
  consumption: number; // L/100km
}

export interface RouteDetails {
  distanceOneWayKm: number;
  frequencyDaysPerMonth: number;
  isRoundTrip: boolean;
}

export interface FuelSettings {
  pricePerLiter: number;
  currency: string;
}

export interface OtherCosts {
  serviceIntervalKm: number; // e.g. 15000
  serviceCost: number; // Cost per one standard service
  tireChangeCostYearly: number; // Total yearly cost for changing tires
  unexpectedRepairsYearly: number; // Budget for unexpected repairs
  parkingYearly: number;
  tollsYearly: number;
  insuranceYearly: number; // New: Annual Insurance cost
}

export interface CalculationResult {
  monthlyDistance: number;
  yearlyDistance: number;
  
  // Monthly Averages for the Big Card
  monthlyTotalCost: number;
  monthlyFuelCost: number;
  
  // Yearly Breakdowns for the Analysis
  yearlyFuelCost: number;
  yearlyServiceCost: number;
  yearlyTireCost: number;
  yearlyUnexpectedCost: number;
  yearlyParkingCost: number;
  yearlyTollCost: number;
  yearlyInsuranceCost: number; // New
  yearlyTotalCost: number;
  
  // Meta
  servicesPerYear: number;
}

export interface DepreciationYear {
  year: number;
  value: number;
  lossTotal: number;
  lossYearly: number;
}