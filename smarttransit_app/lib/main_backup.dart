import 'package:flutter/material.dart';
import 'dart:math';
import 'dart:ui' show lerpDouble;   // <- ADD THIS LINE


void main() {
  runApp(const SmartTransitApp());
}

class SmartTransitApp extends StatelessWidget {
  const SmartTransitApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartTransit++',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.light,
        primaryColor: const Color(0xFF5B2BE0),
        fontFamily: 'Roboto',
      ),
      home: const LoginPage(),
    );
  }
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> with TickerProviderStateMixin {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  late final AnimationController _busController1;
  late final AnimationController _busController2;

  @override
  void initState() {
    super.initState();
    _busController1 = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();
    _busController2 = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 11),
    )..repeat(reverse: false);
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    _busController1.dispose();
    _busController2.dispose();
    super.dispose();
  }

  void _onSignIn() {
    // placeholder: hook this to your auth API
    final email = _emailCtrl.text.trim();
    final pass = _passCtrl.text;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Signing in as $email (demo)'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Widget _buildInput({
    required String hint,
    required bool obscure,
    required TextEditingController controller,
  }) {
    return Column(
      children: [
        TextField(
          controller: controller,
          obscureText: obscure,
          style: const TextStyle(color: Color(0xFF6039D8)),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(color: Color(0xFFC9B9F9)),
            enabledBorder: const UnderlineInputBorder(
              borderSide: BorderSide(color: Color(0xFFCEBEF8), width: 1.5),
            ),
            focusedBorder: const UnderlineInputBorder(
              borderSide: BorderSide(color: Color(0xFF7B49F1), width: 2.0),
            ),
            contentPadding: const EdgeInsets.symmetric(vertical: 12),
          ),
        ),
        const SizedBox(height: 18),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    final isWide = mq.size.width > 700;

    return Scaffold(
      body: Stack(
        children: [
          // Background gradient
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Color(0xFFF3E9FF),
                  Color(0xFFEBDFFF),
                  Color(0xFFECDEFF),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),

          // Large title top-left (partially offscreen like screenshot)
          Positioned(
            top: -30,
            left: -10,
            child: Transform.scale(
              scale: isWide ? 1.8 : 1.2,
              child: Text(
                'SmartTransit++',
                style: TextStyle(
                  color: const Color(0xFF4B1DBF),
                  fontSize: isWide ? 110 : 56,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5,
                  shadows: const [
                    Shadow(
                      color: Color(0x66A27BFF),
                      blurRadius: 8,
                      offset: Offset(4, 6),
                    ),
                  ],
                ),
              ),
            ),
          ),

          // Main centered card area
          Center(
            child: SingleChildScrollView(
              padding: EdgeInsets.symmetric(
                horizontal: isWide ? mq.size.width * 0.28 : 32,
                vertical: 40,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(height: 40),
                  Text(
                    'Welcome Back',
                    style: TextStyle(
                      color: const Color(0xFF4B1DBF),
                      fontSize: isWide ? 46 : 34,
                      fontWeight: FontWeight.w800,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 26),

                  // inputs
                  _buildInput(
                    hint: 'Email Address',
                    obscure: false,
                    controller: _emailCtrl,
                  ),
                  _buildInput(
                    hint: 'Password',
                    obscure: true,
                    controller: _passCtrl,
                  ),

                  // Sign in button
                  SizedBox(
                    width: 140,
                    height: 52,
                    child: ElevatedButton(
                      onPressed: _onSignIn,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF6B2BFF),
                        elevation: 14,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        shadowColor: const Color(0x66000000),
                      ),
                      child: const Text(
                        'Sign In',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 18),

                  // create one link
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        'No account?',
                        style: TextStyle(color: Color(0xFF6D4ADA)),
                      ),
                      const SizedBox(width: 8),
                      GestureDetector(
                        onTap: () {
                          // navigate to sign up screen later
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Open Create Account (demo)')),
                          );
                        },
                        child: const Text(
                          'Create one',
                          style: TextStyle(
                            color: Color(0xFF5B2BE0),
                            fontWeight: FontWeight.w700,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 46),
                ],
              ),
            ),
          ),

          // Left animated bus (moving left->right)
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _busController1,
              builder: (context, child) {
                final t = _busController1.value;
                final x = lerpDouble(-0.2, 1.05, t)!;
                final y = mq.size.height * 0.65;
                return Transform.translate(
                  offset: Offset(x * mq.size.width, y - mq.size.height * 0.1),
                  child: Opacity(
                    opacity: 0.95,
                    child: BusWidget(
                      scale: isWide ? 1.1 : 0.9,
                      color: const Color(0xFF9E7BFF),
                    ),
                  ),
                );
              },
            ),
          ),

          // Right animated bus (moving right->left, slower)
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _busController2,
              builder: (context, child) {
                final t = _busController2.value;
                final x = lerpDouble(1.05, -0.2, t)!;
                final y = mq.size.height * 0.78;
                return Transform.translate(
                  offset: Offset(x * mq.size.width, y - mq.size.height * 0.06),
                  child: Opacity(
                    opacity: 0.98,
                    child: BusWidget(
                      scale: isWide ? 1.3 : 1.0,
                      color: const Color(0xFF6A4AFF),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// A simple stylized "bus" widget made with containers and icons.
/// It's intentionally simple so no image assets are required.
class BusWidget extends StatelessWidget {
  final double scale;
  final Color color;

  const BusWidget({
    super.key,
    this.scale = 1.0,
    this.color = const Color(0xFF8E6BFF),
  });

  @override
  Widget build(BuildContext context) {
    final width = 160.0 * scale;
    final height = 68.0 * scale;

    return Material(
      color: Colors.transparent,
      child: SizedBox(
        width: width,
        height: height,
        child: Stack(
          children: [
            // body
            Positioned(
              left: 0,
              right: 10 * scale,
              top: 8 * scale,
              bottom: 8 * scale,
              child: Container(
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(14 * scale),
                  boxShadow: [
                    BoxShadow(
                      color: color.withOpacity(0.25),
                      blurRadius: 12 * scale,
                      offset: Offset(0, 6 * scale),
                    )
                  ],
                ),
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 14 * scale, vertical: 8 * scale),
                  child: Row(
                    children: [
                      // windows
                      Expanded(
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children: List.generate(3, (i) {
                            return Container(
                              width: 26 * scale,
                              height: 22 * scale,
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.9),
                                borderRadius: BorderRadius.circular(4 * scale),
                              ),
                            );
                          }),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // front light
            Positioned(
              right: 6 * scale,
              top: height * 0.45 - 6 * scale,
              child: Container(
                width: 9 * scale,
                height: 9 * scale,
                decoration: BoxDecoration(
                  color: Colors.amber.withOpacity(0.95),
                  shape: BoxShape.circle,
                ),
              ),
            ),

            // wheels
            Positioned(
              left: 18 * scale,
              bottom: 2 * scale,
              child: Container(
                width: 22 * scale,
                height: 22 * scale,
                decoration: BoxDecoration(
                  color: Colors.black87,
                  shape: BoxShape.circle,
                ),
              ),
            ),
            Positioned(
              left: 62 * scale,
              bottom: 2 * scale,
              child: Container(
                width: 22 * scale,
                height: 22 * scale,
                decoration: BoxDecoration(
                  color: Colors.black87,
                  shape: BoxShape.circle,
                ),
              ),
            ),
            Positioned(
              right: 26 * scale,
              bottom: 2 * scale,
              child: Container(
                width: 22 * scale,
                height: 22 * scale,
                decoration: BoxDecoration(
                  color: Colors.black87,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
