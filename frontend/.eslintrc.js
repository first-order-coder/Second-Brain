/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  extends: ['next', 'next/core-web-vitals'],
  rules: {
    // Forbid direct backend calls from client code; always use Next proxy
    'no-restricted-syntax': [
      'error',
      {
        selector: "CallExpression[callee.name='fetch'] Literal[value^='/youtube/']",
        message: 'Use /api/youtube/flashcards proxy instead of calling backend relative paths.',
      },
      {
        selector: "Literal[value=/^http:\\/\\/backend:8000/]",
        message: 'Do not call Docker service DNS from the browser; use Next /api proxy.',
      },
      {
        selector: "TemplateLiteral[quasis.0.value.raw=/\\$\\{.*NEXT_PUBLIC_API_URL.*\\}/]",
        message: 'Do not use NEXT_PUBLIC_API_URL in client code; use Next /api proxy routes.',
      },
    ],
  },
};

