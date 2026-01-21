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

export interface CalculationResult {
  monthlyDistance: number;
  monthlyFuelNeeded: number;
  monthlyCost: number;
  yearlyCost: number;
  yearlyDistance: number;
}