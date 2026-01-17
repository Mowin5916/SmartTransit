import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

/// Copilot page: query the backend /api/ask_ai which proxies to the RAG server.
/// By default this file uses BACKEND_BASE for the API host. For emulator testing:
/// - Android emulator: use http://10.0.2.2:5000
/// - iOS simulator: use http://localhost:5000
/// - Real device: replace with your machine IP or deployed Render URL.
///
/// Replace BACKEND_BASE with your deployed backend when ready.
const String BACKEND_BASE = String.fromEnvironment(
  'SMARTTRANSIT_BACKEND',
  defaultValue: 'http://10.0.2.2:5000',
);

class CopilotPage extends StatefulWidget {
  const CopilotPage({Key? key}) : super(key: key);

  @override
  State<CopilotPage> createState() => _CopilotPageState();
}

class _CopilotPageState extends State<CopilotPage> {
  final TextEditingController _controller = TextEditingController();
  bool _loading = false;
  String? _answer;
  List<Map<String, dynamic>> _retrieved = [];
  String? _error;

  Future<void> _askCopilot(String query) async {
    setState(() {
      _loading = true;
      _answer = null;
      _retrieved = [];
      _error = null;
    });

    final uri = Uri.parse('$BACKEND_BASE/api/ask_ai');
    final payload = jsonEncode({"query": query, "top_k": 4});

    try {
      final resp = await http.post(
        uri,
        headers: {"Content-Type": "application/json"},
        body: payload,
      ).timeout(const Duration(seconds: 12));

      if (resp.statusCode != 200) {
        setState(() {
          _error = 'Server returned ${resp.statusCode}';
          _loading = false;
        });
        return;
      }

      final Map<String, dynamic> body = jsonDecode(resp.body);

      // The backend returns `answer` and `retrieved` keys (or an error)
      setState(() {
        _answer = body['answer']?.toString() ?? body['message']?.toString() ?? "No answer.";
        final r = body['retrieved'];
        if (r is List) {
          _retrieved = r.map<Map<String, dynamic>>((x) {
            if (x is Map<String,dynamic>) return x;
            return Map<String, dynamic>.from(x as Map);
          }).toList();
        } else {
          _retrieved = [];
        }
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Network/error: $e';
        _loading = false;
      });
    }
  }

  Widget _buildRetrievedList() {
    if (_retrieved.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 12),
        const Text("Sources & Retrieved Snippets", style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        ..._retrieved.asMap().entries.map((entry) {
          final i = entry.key + 1;
          final item = entry.value;
          final src = item['source'] ?? 'unknown';
          final text = (item['text'] ?? '').toString();
          return Card(
            margin: const EdgeInsets.symmetric(vertical: 6),
            child: Padding(
              padding: const EdgeInsets.all(10.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("[$i] Source: $src", style: const TextStyle(fontSize: 12, color: Colors.black87)),
                  const SizedBox(height: 6),
                  Text(text, style: const TextStyle(fontSize: 13)),
                ],
              ),
            ),
          );
        }).toList(),
      ],
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onSend() {
    final q = _controller.text.trim();
    if (q.isEmpty) return;
    _askCopilot(q);
    FocusScope.of(context).unfocus();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("SmartTransit Copilot"),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 12.0),
        child: Column(
          children: [
            // Input row
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _onSend(),
                    decoration: const InputDecoration(
                      hintText: "Ask Copilot (e.g. 'Why is Route 7 delayed?')",
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                    ),
                    minLines: 1,
                    maxLines: 3,
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _loading ? null : _onSend,
                  child: _loading ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.send),
                )
              ],
            ),

            const SizedBox(height: 14),

            // Answer / error
            if (_error != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(8)),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),

            if (_answer != null)
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("AI Answer", style: TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(8)),
                        child: Text(_answer!, style: const TextStyle(fontSize: 15)),
                      ),
                      _buildRetrievedList(),
                      const SizedBox(height: 18),
                    ],
                  ),
                ),
              ),

            if (!_loading && _answer == null && _error == null)
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: const [
                      Icon(Icons.chat_bubble_outline, size: 48, color: Colors.black12),
                      SizedBox(height: 8),
                      Text("Ask the Copilot a question to get started", style: TextStyle(color: Colors.black45)),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
