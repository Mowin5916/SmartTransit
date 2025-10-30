import 'dart:math';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';

void main() {
  runApp(const SmartTransitApp());
}

class SmartTransitApp extends StatelessWidget {
  const SmartTransitApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'SmartTransit++',
      theme: ThemeData(
        useMaterial3: true,
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

class _LoginPageState extends State<LoginPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller =
        AnimationController(vsync: this, duration: const Duration(seconds: 12))
          ..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  /// 🌟 Title Text — Gradient + Elegant Font
  Widget _brandTitle() {
    final gradient = const LinearGradient(
      colors: [Color(0xFF8B5CF6), Color(0xFF6D28D9)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );

    return ShaderMask(
      shaderCallback: (rect) =>
          gradient.createShader(Rect.fromLTWH(0, 0, rect.width, rect.height)),
      child: Text(
        'SmartTransit++',
        textAlign: TextAlign.center,
        style: GoogleFonts.playfairDisplay(
          fontSize: 42,
          fontWeight: FontWeight.w900,
          fontStyle: FontStyle.italic,
          letterSpacing: -1.5,
          height: 1.0,
          color: Colors.white,
          shadows: [
            Shadow(
              offset: const Offset(0, 3),
              blurRadius: 10,
              color: Colors.purple.shade300.withOpacity(0.6),
            ),
          ],
        ),
      ),
    );
  }

  /// 🚌 Animated Buses
  Widget _animatedBus(double delay, double bottom, double width) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final progress =
            (_controller.value + delay).clamp(0.0, 1.0).toDouble() % 1;
        final screenWidth = MediaQuery.of(context).size.width;
        final xPos = progress * (screenWidth + width) - width;
        return Positioned(
          bottom: bottom,
          left: xPos - 50,
          child: Transform.scale(
            scale: 1.0,
            child: Opacity(opacity: 0.8, child: child),
          ),
        );
      },
      child: SvgPicture.asset(
        'assets/bus.svg',
        width: width,
      ),
    );
  }

  /// 🌸 Glass Login Box
  Widget _loginCard() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(30),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(30),
          margin: const EdgeInsets.symmetric(horizontal: 24),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.2),
            borderRadius: BorderRadius.circular(30),
            border: Border.all(color: Colors.white.withOpacity(0.3)),
            boxShadow: [
              BoxShadow(
                color: Colors.deepPurple.withOpacity(0.2),
                blurRadius: 25,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Welcome Back',
                style: GoogleFonts.inter(
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                  color: const Color(0xFF4C1D95),
                ),
              ),
              const SizedBox(height: 30),
              _buildTextField("Email Address", false),
              const SizedBox(height: 20),
              _buildTextField("Password", true),
              const SizedBox(height: 30),
              _signInButton(),
              const SizedBox(height: 20),
              Text.rich(
                TextSpan(
                  text: 'No account? ',
                  style: GoogleFonts.inter(
                    color: const Color(0xFF4C1D95),
                    fontSize: 16,
                  ),
                  children: [
                    TextSpan(
                      text: 'Create one',
                      style: GoogleFonts.inter(
                        color: const Color(0xFF4C1D95),
                        fontWeight: FontWeight.w700,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// ✏️ Input Fields
  Widget _buildTextField(String hint, bool isPassword) {
    return TextField(
      obscureText: isPassword,
      textAlign: TextAlign.center,
      style: GoogleFonts.inter(
        color: Colors.deepPurple.shade900,
        fontWeight: FontWeight.w500,
      ),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: GoogleFonts.inter(
          color: Colors.purple.shade200,
          fontWeight: FontWeight.w400,
        ),
        enabledBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: Colors.purple.shade200, width: 1.5),
        ),
        focusedBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: Color(0xFF6D28D9), width: 2),
        ),
      ),
    );
  }

  /// 🔘 Sign In Button
  Widget _signInButton() {
    return ElevatedButton(
      onPressed: () {},
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF6D28D9),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 80),
        elevation: 10,
        shadowColor: Colors.purpleAccent.withOpacity(0.4),
      ),
      child: Text(
        "Sign In",
        style: GoogleFonts.inter(
          fontSize: 18,
          fontWeight: FontWeight.bold,
          color: Colors.white,
        ),
      ),
    );
  }

  /// 🌈 Full Screen Layout
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3E8FF),
      body: Stack(
        children: [
          // Animated bubbles
          ...List.generate(8, (index) {
            final random = Random(index);
            final top = random.nextDouble() * 800;
            final left = random.nextDouble() * 400;
            final size = random.nextDouble() * 12 + 6;
            return AnimatedBuilder(
              animation: _controller,
              builder: (_, __) {
                final t = _controller.value + index / 8;
                final dy = sin(t * 2 * pi) * 15;
                return Positioned(
                  top: top + dy,
                  left: left,
                  child: Container(
                    width: size,
                    height: size,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.5),
                      shape: BoxShape.circle,
                    ),
                  ),
                );
              },
            );
          }),

          // Moving buses
          _animatedBus(0.0, 60, 120),
          _animatedBus(0.5, 120, 150),

          // SmartTransit Title
          Positioned(
            top: MediaQuery.of(context).size.height * 0.10,
            left: 0,
            right: 0,
            child: Center(child: _brandTitle()),
          ),

          // Login card
          Align(
            alignment: Alignment.center,
            child: _loginCard(),
          ),
        ],
      ),
    );
  }
}
