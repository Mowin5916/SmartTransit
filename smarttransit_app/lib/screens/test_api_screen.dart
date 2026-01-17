import 'package:flutter/material.dart';
import '../services/api.dart';

class TestAPIScreen extends StatefulWidget {
  const TestAPIScreen({super.key});

  @override
  State<TestAPIScreen> createState() => _TestAPIScreenState();
}

class _TestAPIScreenState extends State<TestAPIScreen> {
  String _result = "Tap the button to test your SmartTransit backend";

  Future<void> _testAPI() async {
    setState(() {
      _result = "⏳ Checking API...";
    });

    try {
      final health = await SmartTransitAPI.checkHealth();
      final prediction = await SmartTransitAPI.getPrediction(
        routeId: 1,
        timeSlot: 5,
        weather: 0,
        liveCongestion: 60,
        delayMinutes: 5,
        liveSpeed: 20,
      );

      setState(() {
        _result = "✅ $health\n\n🔮 Prediction:\n$prediction";
      });
    } catch (e) {
      setState(() {
        _result = "❌ Error: $e";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Backend Test"),
        backgroundColor: Colors.deepPurple,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                child: Text(
                  _result,
                  style: const TextStyle(fontSize: 16),
                ),
              ),
            ),
            ElevatedButton.icon(
              onPressed: _testAPI,
              icon: const Icon(Icons.cloud_sync),
              label: const Text("Test SmartTransit API"),
            ),
          ],
        ),
      ),
    );
  }
}
