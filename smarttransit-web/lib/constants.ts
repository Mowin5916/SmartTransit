export const BANGALORE_ROUTES = [
  {
    id: 'R1',
    name: 'Majestic → Whitefield',
    origin: { lat: 12.977439, lng: 77.570839 }, 
    destination: { lat: 12.9804194, lng: 77.7275164 },
    waypoints: [
      { name: 'Corporation Circle', lat: 12.974035, lng: 77.574028 },
      { name: 'Richmond Circle', lat: 12.977996, lng: 77.597445 },
      { name: 'Domlur', lat: 12.971622, lng: 77.641197 },
      { name: 'HAL Main Gate', lat: 12.962708, lng: 77.641018 },
      { name: 'Murugeshpalya', lat: 12.963650, lng: 77.651300 },
      { name: 'Marathahalli Bridge', lat: 12.961605, lng: 77.685460 },
      { name: 'Kundalahalli Gate', lat: 12.978004, lng: 77.706494 },
      { name: 'Graphite India', lat: 12.980650, lng: 77.712050 },
      { name: 'ITPL', lat: 12.982900, lng: 77.747000 }
    ],
    stops_text: "Majestic -> Domlur -> Marathahalli -> Whitefield"
  },
  {
    id: 'R2',
    name: 'Majestic → BTM',
    origin: { lat: 12.977439, lng: 77.570839 }, 
    destination: { lat: 12.916600, lng: 77.610100 }, 
    waypoints: [
      { name: 'Corporation Circle', lat: 12.974035, lng: 77.574028 },
      { name: 'K.R. Circle', lat: 12.966580, lng: 77.575028 },
      { name: 'Lalbagh Main Gate', lat: 12.950418, lng: 77.582823 },
      { name: 'Ashoka Pillar', lat: 12.946200, lng: 77.580400 },
      { name: 'Jayanagar 4th Block', lat: 12.933990, lng: 77.584030 },
      { name: 'MICO Layout', lat: 12.920520, lng: 77.589480 }
    ],
    stops_text: "Majestic -> Jayanagar -> BTM Layout"
  },
  {
    id: 'R3',
    name: 'Silk Board → Hebbal',
    origin: { lat: 12.917823, lng: 77.622477 }, 
    destination: { lat: 13.035781, lng: 77.597008 }, 
    waypoints: [
      { name: 'Agara Junction', lat: 12.924020, lng: 77.623780 },
      { name: 'Bellandur Gate', lat: 12.933520, lng: 77.647220 },
      { name: 'Eco Space', lat: 12.945490, lng: 77.663820 },
      { name: 'Kadubisanahalli', lat: 12.955520, lng: 77.671020 },
      { name: 'Marathahalli Bridge', lat: 12.961605, lng: 77.685460 },
      { name: 'K.R. Puram', lat: 13.006800, lng: 77.678700 },
      { name: 'Tin Factory', lat: 13.011030, lng: 77.617770 },
      { name: 'Manyata Tech Park', lat: 13.028000, lng: 77.577000 }
    ],
    stops_text: "Silk Board -> Marathahalli -> Hebbal"
  },
  {
    id: 'R4',
    name: 'KR Market → Yeshwantpur',
    origin: { lat: 12.964600, lng: 77.577400 }, 
    destination: { lat: 13.012500, lng: 77.555000 }, 
    waypoints: [
      { name: 'K.R. Circle', lat: 12.966580, lng: 77.575028 },
      { name: 'Corporation Circle', lat: 12.974035, lng: 77.574028 },
      { name: 'Majestic (KBS)', lat: 12.977439, lng: 77.570839 },
      { name: 'Swastik', lat: 12.995000, lng: 77.565000 },
      { name: 'Malleshwaram Circle', lat: 13.009420, lng: 77.561040 },
      { name: 'Tata Institute', lat: 13.015000, lng: 77.558000 }
    ],
    stops_text: "KR Market -> Majestic -> Yeshwantpur"
  },
  {
    id: 'R5',
    name: 'Banashankari → ITPL',
    origin: { lat: 12.915400, lng: 77.573600 }, 
    destination: { lat: 12.9804194, lng: 77.7275164 }, 
    waypoints: [
      { name: 'Sangam Circle', lat: 12.916800, lng: 77.586000 },
      { name: 'Ragigudda', lat: 12.919800, lng: 77.584500 },
      { name: 'Central Silk Board', lat: 12.917823, lng: 77.622477 },
      { name: 'Agara Junction', lat: 12.924020, lng: 77.623780 },
      { name: 'Marathahalli Bridge', lat: 12.961605, lng: 77.685460 },
      { name: 'Kundalahalli Gate', lat: 12.978004, lng: 77.706494 },
      { name: 'Vydehi Hospital', lat: 13.000800, lng: 77.716600 }
    ],
    stops_text: "Banashankari -> Silk Board -> ITPL"
  },
  {
    id: 'R6',
    name: 'Electronic City → Majestic',
    origin: { lat: 12.839600, lng: 77.677100 }, 
    destination: { lat: 12.977439, lng: 77.570839 }, 
    waypoints: [
      { name: 'Bommasandra', lat: 12.849000, lng: 77.686000 },
      { name: 'Bommanahalli', lat: 12.914500, lng: 77.617900 },
      { name: 'Central Silk Board', lat: 12.917823, lng: 77.622477 },
      { name: 'Madiwala', lat: 12.922600, lng: 77.617400 },
      { name: 'Dairy Circle', lat: 12.935000, lng: 77.608500 },
      { name: 'Shantinagar', lat: 12.953800, lng: 77.585000 },
      { name: 'Corporation Circle', lat: 12.974035, lng: 77.574028 }
    ],
    stops_text: "Electronic City -> Silk Board -> Majestic"
  },
  {
    id: 'R7',
    name: 'BTM → Marathahalli',
    origin: { lat: 12.916600, lng: 77.610100 }, 
    destination: { lat: 12.955200, lng: 77.698400 }, 
    waypoints: [
      { name: 'Central Silk Board', lat: 12.917823, lng: 77.622477 },
      { name: 'Agara Junction', lat: 12.924020, lng: 77.623780 },
      { name: 'Ibbaluru', lat: 12.931500, lng: 77.636000 },
      { name: 'Bellandur Gate', lat: 12.933520, lng: 77.647220 },
      { name: 'Eco Space', lat: 12.945490, lng: 77.663820 },
      { name: 'Kadubisanahalli', lat: 12.955520, lng: 77.671020 }
    ],
    stops_text: "BTM -> Silk Board -> Marathahalli"
  },
  {
    id: 'R8',
    name: 'Majestic → Airport',
    origin: { lat: 12.977439, lng: 77.570839 }, 
    destination: { lat: 13.199379, lng: 77.710136 }, 
    waypoints: [
      { name: 'Shivananda Circle', lat: 12.990500, lng: 77.566000 },
      { name: 'Mekhri Circle', lat: 13.006000, lng: 77.579500 },
      { name: 'Hebbal', lat: 13.035781, lng: 77.597008 },
      { name: 'Yelahanka', lat: 13.106500, lng: 77.593800 }
    ],
    stops_text: "Majestic -> Hebbal -> Airport"
  },
  {
    id: 'R9',
    name: 'Madiwala → Peenya',
    origin: { lat: 12.922600, lng: 77.617400 }, 
    destination: { lat: 13.028500, lng: 77.519700 }, 
    waypoints: [
      { name: 'Central Silk Board', lat: 12.917823, lng: 77.622477 },
      { name: 'Dairy Circle', lat: 12.935000, lng: 77.608500 },
      { name: 'Shantinagar', lat: 12.953800, lng: 77.585000 },
      { name: 'Corporation Circle', lat: 12.974035, lng: 77.574028 },
      { name: 'Majestic (KBS)', lat: 12.977439, lng: 77.570839 },
      { name: 'Rajajinagar Entrance', lat: 13.004000, lng: 77.556000 },
      { name: 'Mahalakshmi Layout', lat: 13.011500, lng: 77.541500 },
      { name: 'Jalahalli Cross', lat: 13.019000, lng: 77.523500 }
    ],
    stops_text: "Madiwala -> Majestic -> Peenya"
  },
  {
    id: 'R10',
    name: 'Koramangala → MG Road',
    origin: { lat: 12.935000, lng: 77.624000 }, 
    destination: { lat: 12.975600, lng: 77.606600 }, 
    waypoints: [
      { name: 'Forum Mall', lat: 12.927930, lng: 77.629380 },
      { name: 'Dairy Circle', lat: 12.935000, lng: 77.608500 },
      { name: 'Shantinagar', lat: 12.953800, lng: 77.585000 },
      { name: 'Mayo Hall', lat: 12.971000, lng: 77.599000 }
    ],
    stops_text: "Koramangala -> MG Road"
  }
];