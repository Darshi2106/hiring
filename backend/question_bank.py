"""Question bank — MCQ, short-answer and coding modules for various roles.
Seeded once at startup into `question_bank_modules` and `question_bank_questions`.
"""

# Module structure: id, title, category, description, question_ids (populated at seed time)
# Question structure varies by type:
#   mcq: {id, type: 'mcq', question, options[], correct_index, weight}
#   sa:  {id, type: 'sa', question, min_words, weight}
#   code:{id, type: 'code', prompt, starter_code, weight}

_M = {}  # module_id -> module dict
_Q = {}  # qid -> question dict


def _add(module_id, title, category, description, questions):
    ids = []
    for q in questions:
        qid = f"{module_id}::{q['id']}"
        q = {**q, "id": qid, "module_id": module_id}
        _Q[qid] = q
        ids.append(qid)
    _M[module_id] = {
        "id": module_id,
        "title": title,
        "category": category,
        "description": description,
        "question_ids": ids,
        "count": len(ids),
    }


# ---------------- FRONTEND MCQ ----------------
_add("mcq_frontend", "Frontend Fundamentals", "Tech & Eng",
     "React, JavaScript, CSS, browser APIs. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Which React hook is used to memoize an expensive computation?",
     "options": ["useEffect", "useMemo", "useCallback", "useReducer"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "What does `===` do in JavaScript?",
     "options": ["Loose equality (type coercion)", "Strict equality (no coercion)", "Assignment", "Reference identity only"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "In CSS Flexbox, which property aligns items along the main axis?",
     "options": ["align-items", "justify-content", "flex-direction", "align-self"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "What triggers a React component re-render?",
     "options": ["Any function call", "State/prop change or forceUpdate", "DOM click only", "Only setState in class components"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Which HTTP status code indicates 'Unauthorized'?",
     "options": ["400", "401", "403", "404"], "correct_index": 1},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "What is the purpose of a `key` prop in a React list?",
     "options": ["Styling", "Sorting", "Identity for reconciliation", "Random UUID"], "correct_index": 2},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "Which CSS unit is relative to the root element font size?",
     "options": ["em", "px", "rem", "vh"], "correct_index": 2},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "What is the default HTTP method used by `fetch(url)`?",
     "options": ["POST", "GET", "PUT", "OPTIONS"], "correct_index": 1},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "Which is NOT a React hook?",
     "options": ["useState", "useContext", "useHistory", "useCompute"], "correct_index": 3},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "In JS, what does `Array.prototype.map` return?",
     "options": ["A number", "A new array", "The same array mutated", "Undefined"], "correct_index": 1},
])

# ---------------- BACKEND MCQ ----------------
_add("mcq_backend", "Backend Fundamentals", "Tech & Eng",
     "Node/Python, REST, databases, auth. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Which HTTP verb is idempotent?",
     "options": ["POST", "PUT", "PATCH", "CONNECT"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "What does a 502 status typically indicate?",
     "options": ["Client error", "Bad Gateway from upstream server", "Unauthenticated", "Method not allowed"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "In MongoDB, which is the best choice to enforce uniqueness on a field?",
     "options": ["A compound key", "A unique index", "Sharding", "TTL index"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "What is bcrypt primarily used for?",
     "options": ["Symmetric encryption", "Password hashing", "Session token signing", "Hashing large files"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Which library provides async DB access to MongoDB in Python?",
     "options": ["PyMongo (sync)", "Motor", "SQLAlchemy", "asyncpg"], "correct_index": 1},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "In JWT, what is the 'sub' claim?",
     "options": ["Signature", "Subject (user identifier)", "Subscribe channel", "Substitute"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "What does CORS stand for?",
     "options": ["Cross-Origin Resource Sharing", "Custom Origin Response Server", "Cross-Origin Referer Signature", "Configurable Origin Route Set"], "correct_index": 0},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Which is a valid way to invalidate a JWT server-side?",
     "options": ["Rotate secret", "Add to a revocation list", "Reduce clock skew", "Both A and B"], "correct_index": 3},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "SQL: which JOIN returns rows only if there is a match in BOTH tables?",
     "options": ["LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL OUTER JOIN"], "correct_index": 2},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "Which of these is a benefit of using an ORM?",
     "options": ["Automatic vertical scaling", "Query DSL + migrations + type safety", "Faster than raw SQL", "Skips DB constraints"], "correct_index": 1},
])

# ---------------- FULL-STACK ----------------
_add("mcq_fullstack", "Full-stack Senior", "Tech & Eng",
     "System design, tradeoffs, architecture. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 2,
     "question": "Which is best for high-throughput, write-heavy time-series data?",
     "options": ["MongoDB", "TimescaleDB / InfluxDB", "SQLite", "Redis-only"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 2,
     "question": "Best practice for storing secrets in production?",
     "options": ["Hardcode in source", "Env vars via secret manager", "Committed .env file", "Base64 in README"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 2,
     "question": "Which caching strategy is best for a rarely-changing product catalog?",
     "options": ["No cache", "Write-through cache", "CDN + long TTL", "Client-only cache"], "correct_index": 2},
    {"id": "q4", "type": "mcq", "weight": 2,
     "question": "What is the primary purpose of a CI pipeline?",
     "options": ["Run tests + build artifacts on every commit", "Deploy to prod always", "Manage secrets", "Send emails"], "correct_index": 0},
    {"id": "q5", "type": "mcq", "weight": 2,
     "question": "Which pattern helps decouple services asynchronously?",
     "options": ["Direct REST call", "Synchronous RPC", "Message queue / event bus", "Shared DB"], "correct_index": 2},
    {"id": "q6", "type": "mcq", "weight": 2,
     "question": "Which is a symptom of N+1 query problem?",
     "options": ["Extra round trips per list item", "Slow single query", "Missing index only", "Deadlock"], "correct_index": 0},
    {"id": "q7", "type": "mcq", "weight": 2,
     "question": "Which is best for feature flags at scale?",
     "options": ["`if user.email==...`", "Config file redeploys", "Feature-flag service (LaunchDarkly, Unleash)", "Cookies"], "correct_index": 2},
    {"id": "q8", "type": "mcq", "weight": 2,
     "question": "What does 'eventual consistency' mean?",
     "options": ["All reads are always consistent", "Reads may lag behind writes but converge", "Writes are lost", "Only one node"], "correct_index": 1},
    {"id": "q9", "type": "mcq", "weight": 2,
     "question": "Best practice for API versioning?",
     "options": ["Break clients silently", "URL or header-based versions with deprecation policy", "Rename all endpoints", "Change response type"], "correct_index": 1},
    {"id": "q10", "type": "mcq", "weight": 2,
     "question": "For a chat app with 10M users, what's the right transport?",
     "options": ["HTTP polling every 100ms", "WebSockets / SSE", "Cron jobs", "Email"], "correct_index": 1},
])

# ---------------- ML BASICS ----------------
_add("mcq_ml", "Machine Learning Basics", "Tech & Eng",
     "Supervised/unsupervised, metrics, pipelines. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Which is a supervised learning task?",
     "options": ["K-means clustering", "PCA", "Image classification", "Anomaly detection via autoencoders"], "correct_index": 2},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "What does the F1 score balance?",
     "options": ["Precision and recall", "Accuracy and loss", "Bias and variance", "Train and test"], "correct_index": 0},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "Which is a symptom of overfitting?",
     "options": ["High train loss, high test loss", "Low train loss, high test loss", "Low train and test loss", "High train loss, low test loss"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "Which framework is primarily used for tensor computation with autograd?",
     "options": ["OpenCV", "PyTorch", "Pandas", "NLTK"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "What is 'inter-annotator agreement' used for?",
     "options": ["Model accuracy", "Annotation consistency", "Training speed", "Data size"], "correct_index": 1},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "Which is best to reduce overfitting on small datasets?",
     "options": ["More parameters", "Data augmentation + regularization", "Removing validation set", "Higher learning rate"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "For imbalanced binary classification, which metric is misleading?",
     "options": ["F1", "Precision", "Accuracy", "ROC-AUC"], "correct_index": 2},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "What does 'batch normalization' primarily do?",
     "options": ["Normalize dataset", "Normalize inputs to a layer during training", "Compress model", "Regularize labels"], "correct_index": 1},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "Which is a common activation for a binary classifier output layer?",
     "options": ["ReLU", "Sigmoid", "Softmax", "Tanh"], "correct_index": 1},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "Which technique measures how features contribute to a prediction?",
     "options": ["SHAP", "Adam", "Batch size", "Dropout"], "correct_index": 0},
])

# ---------------- COMPUTER VISION ----------------
_add("mcq_cv", "Computer Vision", "Tech & Eng",
     "CV concepts, object detection, augmentation. 8 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Which architecture family is standard for object detection?",
     "options": ["Transformers only", "YOLO / Faster-RCNN / DETR", "GAN", "RNN"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "IoU stands for:",
     "options": ["Iteration of Units", "Intersection over Union", "Index of Update", "Instance of Utility"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "Which technique increases dataset diversity without new labels?",
     "options": ["Sharding", "Data augmentation (crop/rotate/color-jitter)", "Fine-tuning", "Quantization"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "COCO dataset is primarily used for:",
     "options": ["ASR", "Object detection, segmentation, keypoints", "Recommendation", "Language modeling"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "What does 'non-max suppression' do?",
     "options": ["Increase learning rate", "Remove overlapping bounding boxes with lower scores", "Reduce network size", "Train faster"], "correct_index": 1},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "A common metric for object detection is:",
     "options": ["mAP", "BLEU", "Perplexity", "Rouge-L"], "correct_index": 0},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "Semantic segmentation outputs:",
     "options": ["A single label per image", "A label per pixel", "A bounding box per object", "A caption"], "correct_index": 1},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Which sensor pairing is common in ADAS?",
     "options": ["Camera + Lidar + Radar", "Only mic", "Only GPS", "Only barometer"], "correct_index": 0},
])

# ---------------- DSA ----------------
_add("mcq_dsa", "Data Structures & Algorithms", "Tech & Eng",
     "Time complexity, common structures. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Average time complexity of hashmap lookup?",
     "options": ["O(1)", "O(log n)", "O(n)", "O(n log n)"], "correct_index": 0},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "Which is a stable sort?",
     "options": ["Quicksort", "Mergesort", "Heapsort", "Selection sort"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "Time complexity of binary search on sorted array?",
     "options": ["O(1)", "O(log n)", "O(n)", "O(n log n)"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "Best structure for FIFO ordering?",
     "options": ["Stack", "Queue", "Set", "HashMap"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Which traversal visits root before subtrees?",
     "options": ["Inorder", "Postorder", "Preorder", "Level-order only"], "correct_index": 2},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "Which algorithm finds shortest path with non-negative weights?",
     "options": ["Bellman-Ford", "Dijkstra", "Kruskal", "Floyd-Warshall"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "Fibonacci with memoization: time complexity?",
     "options": ["O(2^n)", "O(n)", "O(n log n)", "O(1)"], "correct_index": 1},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Which data structure is best for autocomplete/prefix search?",
     "options": ["Hash set", "Trie", "Heap", "Linked list"], "correct_index": 1},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "Which is NOT true about a min-heap?",
     "options": ["Root is smallest", "Push is O(log n)", "Sorted array", "Pop is O(log n)"], "correct_index": 2},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "Which technique is used to detect cycles in a linked list?",
     "options": ["DFS", "Floyd's tortoise & hare", "Union-find", "Topological sort"], "correct_index": 1},
])

# ---------------- SQL ----------------
_add("mcq_sql", "SQL Fundamentals", "Tech & Eng",
     "Joins, aggregations, indexes. 8 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Which clause filters GROUP BY results?",
     "options": ["WHERE", "HAVING", "SELECT", "ORDER BY"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "Which JOIN keeps rows from the left table even without match?",
     "options": ["INNER JOIN", "LEFT JOIN", "CROSS JOIN", "RIGHT JOIN"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "Which is NOT an aggregate function?",
     "options": ["SUM", "AVG", "COUNT", "SUBSTRING"], "correct_index": 3},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "What does an INDEX primarily improve?",
     "options": ["Storage size", "Read performance", "Write performance", "Backup speed"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Which command permanently removes rows and cannot be rolled back (in most DBs)?",
     "options": ["DELETE", "TRUNCATE", "DROP TABLE", "Both B & C"], "correct_index": 3},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "Which normal form deals with removing partial dependency?",
     "options": ["1NF", "2NF", "3NF", "BCNF"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "SELECT COUNT(*) vs COUNT(col_x) — the difference?",
     "options": ["Identical", "COUNT(col_x) excludes NULLs", "COUNT(*) is slower always", "COUNT(*) excludes NULLs"], "correct_index": 1},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Which is a window function keyword?",
     "options": ["OVER", "UNION", "MERGE", "USING"], "correct_index": 0},
])

# ---------------- APTITUDE QUANT ----------------
_add("mcq_aptitude_quant", "Aptitude — Quantitative", "General",
     "Numbers, ratios, percentages. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "If x = 3 and y = 4, then x² + y² = ?",
     "options": ["25", "12", "7", "49"], "correct_index": 0},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "20% of 250 = ?",
     "options": ["25", "50", "45", "62.5"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "A train travels 120 km in 2 hours. Its average speed?",
     "options": ["50 km/h", "60 km/h", "40 km/h", "80 km/h"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "A price is discounted 25% to ₹300. Original price?",
     "options": ["₹375", "₹400", "₹450", "₹425"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Simplify: 3/4 + 1/2 = ?",
     "options": ["1", "5/4", "1 1/4", "Both B and C"], "correct_index": 3},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "The ratio 12:16 in simplest form is:",
     "options": ["6:8", "3:4", "2:3", "4:5"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "If a machine can annotate 100 items in 5 hours, how many in 12 hours?",
     "options": ["200", "240", "220", "260"], "correct_index": 1},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Compound interest on ₹1000 at 10% for 2 years:",
     "options": ["₹200", "₹210", "₹220", "₹100"], "correct_index": 1},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "Average of 4, 8, 12, 16 = ?",
     "options": ["8", "10", "12", "14"], "correct_index": 1},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "√144 + √25 = ?",
     "options": ["15", "17", "19", "13"], "correct_index": 1},
])

# ---------------- APTITUDE LOGICAL ----------------
_add("mcq_aptitude_logical", "Aptitude — Logical Reasoning", "General",
     "Patterns, sequences, deduction. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Complete the sequence: 2, 6, 12, 20, __",
     "options": ["28", "30", "32", "24"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "Odd one out: Cat, Dog, Cow, Rose",
     "options": ["Cat", "Dog", "Rose", "Cow"], "correct_index": 2},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?",
     "options": ["Yes", "No", "Only some", "Cannot be determined"], "correct_index": 0},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "In a row of 20, A is 7th from left. Position from right?",
     "options": ["12th", "13th", "14th", "15th"], "correct_index": 2},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Complete: AB, CD, EF, __",
     "options": ["FG", "GH", "IJ", "HI"], "correct_index": 1},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "Water : Liquid :: Ice : ?",
     "options": ["Gas", "Solid", "Cold", "Cloud"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "If today is Monday, what day is 100 days from today?",
     "options": ["Tuesday", "Wednesday", "Thursday", "Friday"], "correct_index": 1},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Book is to Reading as Fork is to __?",
     "options": ["Kitchen", "Eating", "Drawing", "Dish"], "correct_index": 1},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "Complete: 1, 1, 2, 3, 5, 8, __",
     "options": ["11", "12", "13", "14"], "correct_index": 2},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "If MONDAY = 123456 and DAY = 456, what is MOND?",
     "options": ["1234", "2345", "1235", "1204"], "correct_index": 0},
])

# ---------------- APTITUDE VERBAL ----------------
_add("mcq_aptitude_verbal", "Aptitude — Verbal", "General",
     "Grammar, vocab, comprehension. 8 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "Synonym of 'meticulous':",
     "options": ["Careless", "Precise", "Fast", "Loud"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "Antonym of 'benevolent':",
     "options": ["Kind", "Malevolent", "Generous", "Cheerful"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "Which sentence is grammatically correct?",
     "options": ["She don't like tea", "She doesn't likes tea", "She doesn't like tea", "She not like tea"], "correct_index": 2},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "Pick the correctly spelled word:",
     "options": ["Accomodate", "Accommodate", "Acommodate", "Accomadate"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Choose the odd one:",
     "options": ["Painter", "Sculptor", "Architect", "Bicycle"], "correct_index": 3},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "'They _____ arrived when it started to rain.' Fill:",
     "options": ["has just", "had just", "have just", "just have"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "Idiom 'break the ice' means:",
     "options": ["Start a conversation", "Cool a drink", "Cancel a meeting", "Repair something"], "correct_index": 0},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Meaning of 'ubiquitous':",
     "options": ["Rare", "Present everywhere", "Fragile", "Hidden"], "correct_index": 1},
])

# ---------------- SALES ----------------
_add("mcq_sales", "Sales & Business Acumen", "Business & Sales",
     "B2B sales, discovery, pipeline. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "In B2B sales, BANT stands for:",
     "options": ["Budget, Authority, Need, Timing", "Business, Account, Need, Team", "Buyer, Advocate, Negotiator, Timeline", "Bid, Auction, Notice, Ticket"], "correct_index": 0},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "A well-qualified opportunity typically has:",
     "options": ["Only budget", "Champion + pain + timeline + budget", "One reference", "Only urgency"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "Which is a discovery question?",
     "options": ["Do you like our product?", "What is your biggest data-quality bottleneck today?", "Can you sign the contract?", "What is your favorite color?"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "A 'multi-threaded' deal is one where the seller:",
     "options": ["Talks only to procurement", "Engages multiple stakeholders in the buying committee", "Uses many channels", "Sends many emails"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "Best practice for handling price objection:",
     "options": ["Immediate discount", "Restate value + quantify ROI", "Silent treatment", "Escalate to CEO"], "correct_index": 1},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "Pipeline coverage of 3x means:",
     "options": ["Close-rate 300%", "Pipeline is 3× the quota", "3 salespeople", "3-week sprint"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "Ideal Customer Profile (ICP) focuses on:",
     "options": ["Persona of one buyer", "Types of accounts most likely to succeed", "Feature list", "Pricing"], "correct_index": 1},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Which stage is a deal in when a signed order form is received?",
     "options": ["Prospect", "Qualification", "Closed-won", "Renewal"], "correct_index": 2},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "Best signal that a prospect is a champion:",
     "options": ["They introduce you to power", "They ghost your emails", "They cc procurement first", "They ask for a demo"], "correct_index": 0},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "Annual Contract Value (ACV) is:",
     "options": ["Total revenue over lifetime", "Yearly recurring contract value", "Cash today only", "One-time services"], "correct_index": 1},
])

# ---------------- OPERATIONS ----------------
_add("mcq_operations", "Operations & Platform Ops", "Operations",
     "SLA, incident, throughput. 10 questions.", [
    {"id": "q1", "type": "mcq", "weight": 1,
     "question": "SLA stands for:",
     "options": ["System Level Access", "Service Level Agreement", "Standard List Amount", "Server Latency Alert"], "correct_index": 1},
    {"id": "q2", "type": "mcq", "weight": 1,
     "question": "MTTR measures:",
     "options": ["Mean Time to Register", "Mean Time to Repair/Restore", "Max Total Task Runtime", "Median TTL"], "correct_index": 1},
    {"id": "q3", "type": "mcq", "weight": 1,
     "question": "Which is a leading indicator for annotation-pipeline quality?",
     "options": ["Ticket count", "Inter-annotator agreement", "Employee headcount", "Server uptime"], "correct_index": 1},
    {"id": "q4", "type": "mcq", "weight": 1,
     "question": "During an outage the first step for on-call is:",
     "options": ["Blame post", "Ack + assess impact + declare severity", "Refactor code", "Write a blog"], "correct_index": 1},
    {"id": "q5", "type": "mcq", "weight": 1,
     "question": "A blameless post-mortem focuses on:",
     "options": ["Who to fire", "System + process improvement", "Adding tests only", "PR templates"], "correct_index": 1},
    {"id": "q6", "type": "mcq", "weight": 1,
     "question": "Which metric measures request success percentage?",
     "options": ["Latency P99", "Availability / success ratio", "Throughput", "Error budget"], "correct_index": 1},
    {"id": "q7", "type": "mcq", "weight": 1,
     "question": "An error budget of 0.1% per month allows how many minutes of downtime?",
     "options": ["~4.3 min", "~43 min", "~430 min", "~1 min"], "correct_index": 1},
    {"id": "q8", "type": "mcq", "weight": 1,
     "question": "Which is a benefit of runbooks?",
     "options": ["Reduce on-call cognitive load", "Increase paging", "Slow down responders", "Nothing"], "correct_index": 0},
    {"id": "q9", "type": "mcq", "weight": 1,
     "question": "In throughput terms, RPS stands for:",
     "options": ["Requests Per Second", "Reports Per Slot", "Rows Per Session", "Retries Per Server"], "correct_index": 0},
    {"id": "q10", "type": "mcq", "weight": 1,
     "question": "Rolling deploy vs blue/green: which minimizes rollback time?",
     "options": ["Rolling", "Blue/green", "Both same", "Neither"], "correct_index": 1},
])

# ---------------- SHORT-ANSWER BANK ----------------
_add("sa_behavioral", "Behavioral — General", "General",
     "Ownership, conflict, learning. 6 questions.", [
    {"id": "q1", "type": "sa", "weight": 1, "min_words": 60,
     "question": "Describe a time you took ownership of a project outside your comfort zone. What did you learn?"},
    {"id": "q2", "type": "sa", "weight": 1, "min_words": 60,
     "question": "Tell us about a conflict you resolved on your team. What was the outcome?"},
    {"id": "q3", "type": "sa", "weight": 1, "min_words": 50,
     "question": "How do you decide when 'good enough' is good enough vs. shipping later?"},
    {"id": "q4", "type": "sa", "weight": 1, "min_words": 50,
     "question": "Describe a mistake you made at work. How did you recover?"},
    {"id": "q5", "type": "sa", "weight": 1, "min_words": 60,
     "question": "How do you approach learning a completely new domain quickly?"},
    {"id": "q6", "type": "sa", "weight": 1, "min_words": 50,
     "question": "Tell us about a time you disagreed with a manager. How did you handle it?"},
])

_add("sa_tech", "Short-answer — Tech", "Tech & Eng", "Technical scenarios. 5 questions.", [
    {"id": "q1", "type": "sa", "weight": 1, "min_words": 60,
     "question": "How would you design quality control for a multimodal annotation pipeline handling 100k+ items per week?"},
    {"id": "q2", "type": "sa", "weight": 1, "min_words": 60,
     "question": "Walk us through how you would debug a production API with intermittent 502s."},
    {"id": "q3", "type": "sa", "weight": 1, "min_words": 60,
     "question": "Describe a technical decision you regret. What would you do differently?"},
    {"id": "q4", "type": "sa", "weight": 1, "min_words": 60,
     "question": "Explain a system you have designed and its main bottleneck."},
    {"id": "q5", "type": "sa", "weight": 1, "min_words": 60,
     "question": "How do you approach code review to be both fast and thorough?"},
])

_add("sa_sales", "Short-answer — Sales", "Business & Sales", "Sales scenarios. 4 questions.", [
    {"id": "q1", "type": "sa", "weight": 1, "min_words": 60,
     "question": "Walk us through how you would prospect a Fortune-500 automotive company for our ADAS data services."},
    {"id": "q2", "type": "sa", "weight": 1, "min_words": 60,
     "question": "A prospect asks for a 40% discount to close in Q4. How do you respond?"},
    {"id": "q3", "type": "sa", "weight": 1, "min_words": 60,
     "question": "Describe your largest closed deal — what was pivotal?"},
    {"id": "q4", "type": "sa", "weight": 1, "min_words": 60,
     "question": "How do you rebuild trust with a customer whose renewal you are at risk of losing?"},
])

# ---------------- CODING TASKS ----------------
_add("code_python_beginner", "Coding — Python (Beginner)", "Tech & Eng",
     "Fundamentals. 1 task.", [
    {"id": "q1", "type": "code", "weight": 3,
     "prompt": "Write a function `count_duplicates(arr)` that returns the number of values in the integer array that appear more than once (count of DISTINCT duplicate values, not total duplicates).",
     "starter_code": "def count_duplicates(arr):\n    # your code here\n    pass\n\n# Examples:\n# count_duplicates([1,2,2,3]) -> 1\n# count_duplicates([1,1,2,2,3]) -> 2\n# count_duplicates([1,2,3]) -> 0\n"},
])

_add("code_python_intermediate", "Coding — Python (Intermediate)", "Tech & Eng",
     "String parsing + data structures. 1 task.", [
    {"id": "q1", "type": "code", "weight": 5,
     "prompt": "Given a list of log lines in the format 'YYYY-MM-DD HH:MM:SS LEVEL MESSAGE', write `top_errors_per_day(lines, n=3)` returning a dict of {date: [top n most-frequent ERROR messages]}. Only ERROR-level messages count.",
     "starter_code": "from collections import defaultdict, Counter\n\ndef top_errors_per_day(lines, n=3):\n    # your code here\n    pass\n"},
])

_add("code_javascript_async", "Coding — JavaScript / Async", "Tech & Eng",
     "Promises, error handling. 1 task.", [
    {"id": "q1", "type": "code", "weight": 4,
     "prompt": "Write an async JS function `fetchWithRetry(url, options={}, retries=3, backoffMs=500)` that fetches the URL and retries on non-2xx / network error with exponential backoff. On final failure it should throw the last error.",
     "starter_code": "async function fetchWithRetry(url, options = {}, retries = 3, backoffMs = 500) {\n  // your code here\n}\n"},
])

_add("code_dsa", "Coding — Data Structures", "Tech & Eng", "Classic DSA. 1 task.", [
    {"id": "q1", "type": "code", "weight": 5,
     "prompt": "Implement `lru_cache_class(capacity)` that returns an object supporting `get(key)` and `put(key, value)` with O(1) average complexity, evicting the least-recently-used key when capacity is exceeded.",
     "starter_code": "def lru_cache_class(capacity):\n    # Return an object with .get(key) and .put(key, value)\n    pass\n"},
])

_add("code_sql", "Coding — SQL Query", "Tech & Eng", "SQL query challenge.", [
    {"id": "q1", "type": "code", "weight": 3,
     "prompt": "Given tables `applications(id, job_id, candidate_id, created_at)` and `jobs(id, title, department)`, write a SQL query that returns, for each department, the top 3 job titles by number of applications in the last 30 days.",
     "starter_code": "-- Your SQL here\n"},
])

_add("code_ml_pipeline", "Coding — ML Pipeline", "Tech & Eng",
     "Data + model boilerplate. 1 task.", [
    {"id": "q1", "type": "code", "weight": 5,
     "prompt": "Using scikit-learn, write `train_and_score(df, target_col)` that: 1) splits into train/test 80/20, 2) fits a RandomForestClassifier with 100 trees, 3) returns test-set F1 (weighted). Use random_state=42.",
     "starter_code": "from sklearn.ensemble import RandomForestClassifier\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import f1_score\n\ndef train_and_score(df, target_col):\n    # your code here\n    pass\n"},
])


def all_modules():
    return list(_M.values())


def get_module(module_id):
    return _M.get(module_id)


def get_question(qid):
    return _Q.get(qid)


def get_questions_by_ids(qids):
    return [_Q[q] for q in qids if q in _Q]


async def seed_question_bank(db):
    """Idempotent seed."""
    count = await db.question_bank.count_documents({})
    if count > 0:
        return
    docs = []
    for m in _M.values():
        docs.append({
            **m,
            "questions": [_Q[qid] for qid in m["question_ids"]],
        })
    if docs:
        await db.question_bank.insert_many(docs)
