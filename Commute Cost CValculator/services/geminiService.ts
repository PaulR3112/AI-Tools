import { GoogleGenAI, Type } from "@google/genai";
import { CarSpecs } from "../types";

// Initialize Gemini Client
const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

const cleanJson = (text: string) => {
  try {
    // First try to find a JSON block
    const match = text.match(/```json\n([\s\S]*?)\n```/);
    if (match) {
      return match[1];
    }
    // Fallback: simple brace finding
    const firstOpen = text.indexOf('{');
    const lastClose = text.lastIndexOf('}');
    if (firstOpen !== -1 && lastClose !== -1) {
      return text.substring(firstOpen, lastClose + 1);
    }
    return text;
  } catch (e) {
    return text;
  }
};

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
    // Using gemini-2.0-flash-exp for better stability with Google Search tools
    const model = 'gemini-2.0-flash-exp';
    
    const response = await ai.models.generateContent({
      model,
      contents: `Calculate the driving distance between ${start} and ${end} using Google Search.
      Return the result as a JSON object with the key "distanceKm" (number).`,
      config: {
        tools: [{ googleSearch: {} }],
      },
    });

    if (response.text) {
      const cleaned = cleanJson(response.text);
      return JSON.parse(cleaned);
    }
    return null;
  } catch (error) {
    console.error("Error fetching route:", error);
    return null;
  }
};

export const getRouteFromUrl = async (url: string): Promise<{ distanceKm: number; start?: string; end?: string } | null> => {
  try {
    // Upgraded to gemini-3-pro-preview for complex reasoning required to solve short links.
    const model = 'gemini-3-pro-preview';
    
    const response = await ai.models.generateContent({
      model,
      contents: `User provided this Google Maps URL: "${url}"
      
      Your specific task:
      1. Perform a Google Search for this EXACT URL.
      2. Look at the title and snippet of the search result. It often contains text like "Route from City A to City B".
      3. If the URL is a short link (maps.app.goo.gl), the search result title is the most reliable way to find the destination.
      4. Extract the Start and End locations specifically from the search title/snippet.
      5. Calculate the driving distance between these two locations.
      
      CRITICAL: Do not guess cities if the search result does not explicitly show a route. If you cannot find the route, return null.

      Return ONLY a JSON object with:
      - "start": string (The extracted origin name)
      - "end": string (The extracted destination name)
      - "distanceKm": number (The driving distance)
      
      Example Search Result Title: "Route from Prague to Brno - Google Maps" -> start: Prague, end: Brno.`,
      config: {
        tools: [{ googleSearch: {} }],
      },
    });

    if (response.text) {
      const cleaned = cleanJson(response.text);
      return JSON.parse(cleaned);
    }
    return null;
  } catch (error) {
    console.error("Error analyzing route URL:", error);
    return null;
  }
};