import { GoogleGenAI, Type } from "@google/genai";
import { CarSpecs } from "../types";

// Initialize Gemini Client
const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

export const getCarConsumptionEstimate = async (carDescription: string): Promise<CarSpecs | null> => {
  try {
    const model = 'gemini-3-flash-preview';
    
    const response = await ai.models.generateContent({
      model,
      contents: `Estimate the combined fuel consumption (L/100km) for this vehicle: "${carDescription}". 
      Return a realistic average based on real-world data.`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            make: { type: Type.STRING },
            model: { type: Type.STRING },
            year: { type: Type.STRING },
            fuelType: { type: Type.STRING },
            consumption: { type: Type.NUMBER, description: "Average combined consumption in Liters per 100km" },
          },
          required: ["make", "model", "consumption"],
        },
      },
    });

    if (response.text) {
      return JSON.parse(response.text) as CarSpecs;
    }
    return null;
  } catch (error) {
    console.error("Error fetching car specs:", error);
    return null;
  }
};

export const getRouteEstimate = async (start: string, end: string): Promise<{ distanceKm: number } | null> => {
  try {
    const model = 'gemini-3-flash-preview';
    
    // We use search grounding to find the actual distance
    const response = await ai.models.generateContent({
      model,
      contents: `What is the driving distance in kilometers between ${start} and ${end}? Return just the number.`,
      config: {
        tools: [{ googleSearch: {} }],
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            distanceKm: { type: Type.NUMBER, description: "Distance in KM" },
          },
        },
      },
    });

    if (response.text) {
      return JSON.parse(response.text);
    }
    return null;
  } catch (error) {
    console.error("Error fetching route:", error);
    return null;
  }
};