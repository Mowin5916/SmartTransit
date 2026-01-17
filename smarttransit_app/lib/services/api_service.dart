// lib/services/api_service.dart
import 'dart:async'; // <-- needed for TimeoutException
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ApiService {
  // Use your Render URL (keep this updated if you redeploy)
  static const String baseUrl = 'https://smarttransit-d5c0.onrender.com';

  // Increase timeout so mobile requests have more time
  static const Duration requestTimeout = Duration(seconds: 20);

  /// Call /predict endpoint and return decoded JSON.
  static Future<Map<String, dynamic>> predict({
    required int routeId,
    required int timeSlot,
    required int weather,
    required double liveCongestion,
    required double delayMinutes,
    required double liveSpeed,
  }) async {
    final uri = Uri.parse('$baseUrl/predict').replace(queryParameters: {
      'route_id': routeId.toString(),
      'time_slot': timeSlot.toString(),
      'weather': weather.toString(),
      'live_congestion': liveCongestion.toString(),
      'delay_minutes': delayMinutes.toString(),
      'live_speed': liveSpeed.toString(),
    });

    try {
      final response = await http.get(uri).timeout(
        requestTimeout,
        onTimeout: () {
          // Create and throw a TimeoutException (from dart:async)
          throw TimeoutException(
            'Request to server timed out after ${requestTimeout.inSeconds}s',
            requestTimeout,
          );
        },
      );

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final Map<String, dynamic> body = json.decode(response.body);
        return body;
      } else {
        throw HttpException(
            'Server returned status ${response.statusCode}: ${response.reasonPhrase ?? ''}');
      }
    } on SocketException catch (e) {
      throw Exception('Network error: ${e.message}. Is your device online?');
    } on TimeoutException catch (e) {
      throw Exception('Timeout: ${e.message}');
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }
}
