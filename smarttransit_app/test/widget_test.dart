import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:smarttransit_app/main.dart';

void main() {
  testWidgets('App launches and shows login title', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const SmartTransitApp());

    // Verify that the login title 'Welcome Back' is present.
    expect(find.text('Welcome Back'), findsOneWidget);

    // Enter email and password
    await tester.enterText(find.byType(TextFormField).first, 'anika@example.com');
    await tester.enterText(find.byType(TextFormField).last, 'password123');

    // Tap Sign In
    await tester.tap(find.text('Sign In'));
    await tester.pumpAndSettle();

    // After login we should see the home page greeting
    expect(find.text('Welcome to SmartTransit++'), findsOneWidget);
  });
}
