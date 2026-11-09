"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(() => {
var exports = {};
exports.id = "instrumentation";
exports.ids = ["instrumentation"];
exports.modules = {

/***/ "(instrument)/./instrumentation.ts":
/*!****************************!*\
  !*** ./instrumentation.ts ***!
  \****************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   register: () => (/* binding */ register)\n/* harmony export */ });\nasync function register() {\n    if (true) {\n        const { serverEnv } = await Promise.all(/*! import() */[__webpack_require__.e(\"vendor-chunks/next\"), __webpack_require__.e(\"_instrument_lib_server_env_ts\")]).then(__webpack_require__.bind(__webpack_require__, /*! @/lib/server/env */ \"(instrument)/./lib/server/env.ts\"));\n        serverEnv();\n    }\n}\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKGluc3RydW1lbnQpLy4vaW5zdHJ1bWVudGF0aW9uLnRzIiwibWFwcGluZ3MiOiI7Ozs7QUFBTyxlQUFlQTtJQUNwQixJQUFJQyxJQUFxQyxFQUFFO1FBQ3pDLE1BQU0sRUFBRUcsU0FBUyxFQUFFLEdBQUcsTUFBTSxpUEFBMEI7UUFDdERBO0lBQ0Y7QUFDRiIsInNvdXJjZXMiOlsiL1VzZXJzL3BsYW5lYnl0ZS9Eb2N1bWVudHMvUHJvamVjdHMvcGxhbmVieXRlLWxlYWRnZW4vZGFzaGJvYXJkL2luc3RydW1lbnRhdGlvbi50cyJdLCJzb3VyY2VzQ29udGVudCI6WyJleHBvcnQgYXN5bmMgZnVuY3Rpb24gcmVnaXN0ZXIoKSB7XG4gIGlmIChwcm9jZXNzLmVudi5ORVhUX1JVTlRJTUUgPT09IFwibm9kZWpzXCIpIHtcbiAgICBjb25zdCB7IHNlcnZlckVudiB9ID0gYXdhaXQgaW1wb3J0KFwiQC9saWIvc2VydmVyL2VudlwiKTtcbiAgICBzZXJ2ZXJFbnYoKTtcbiAgfVxufVxuIl0sIm5hbWVzIjpbInJlZ2lzdGVyIiwicHJvY2VzcyIsImVudiIsIk5FWFRfUlVOVElNRSIsInNlcnZlckVudiJdLCJpZ25vcmVMaXN0IjpbXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///(instrument)/./instrumentation.ts\n");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("./webpack-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = (__webpack_exec__("(instrument)/./instrumentation.ts"));
module.exports = __webpack_exports__;

})();