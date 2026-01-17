import 'dart:convert';
import 'package:http/http.dart' as http;

class SmartTransitAPI {
  // 🔗 Backend base URL (your Render deployment)
  static const String baseUrl = "https://smarttransit-d5c0.onrender.com";

  // ✅ Health check (to verify backend is alive)
  static Future<String> checkHealth() async {
    final url = Uri.parse("$baseUrl/");
    final res = await http.get(url);
    if (res.statusCode == 200) {
      return "✅ API Connected: ${res.body}";
    } else {
      throw Exception("❌ API error: ${res.statusCode}");
    }
  }

  // 🧮 Passenger Prediction endpoint
  static Future<Map<String, dynamic>> getPrediction({
    required int routeId,
    required int timeSlot,
    required int weather,
    required int liveCongestion,
    required int delayMinutes,
    required int liveSpeed,
  }) async {
    final url = Uri.parse(
      "$baseUrl/predict"
      "?route_id=$routeId"
      "&time_slot=$timeSlot"
      "&weather=$weather"
      "&live_congestion=$liveCongestion"
      "&delay_minutes=$delayMinutes"
      "&live_speed=$liveSpeed",
    );

    final res = await http.get(url);

    if (res.statusCode == 200) {
      return jsonDecode(res.body);
    } else {
      throw Exception("Prediction failed: ${res.statusCode}");
    }
  }
}
