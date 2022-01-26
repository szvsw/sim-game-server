const { Client, Server } = require("node-osc");

class Connection {
  constructor(io, socket) {
    this.socket = socket;
    this.io = io;

    socket.on("sun-weather", (_data) => {
      _data.ghCallback = "sun-weather";
      _data.args = {
        M: { value: _data.month, type: "integer" },
        D: { value: _data.day, type: "integer" },
        H: { value: _data.hour, type: "number" },
      };
      _data.outs = {
        V: "Vector3D",
      };
      this.io.oscClient.send("/compute", JSON.stringify(_data));
    });

    socket.on("update cost", (_data) => {
      _data.args = {
        building: { value: { ..._data }, type: "json" },
      };
      _data.outs = {
        cost: "number",
        eui: "number",
        model: "string",
      };
      // _data.ghCallback = "cost-calculator";
      _data.ghCallback = "calculate-eui";
      this.io.oscClient.send("/compute", JSON.stringify(_data));
    });

    socket.on("building", (_data) => {
      socket.broadcast.emit("building", _data);
      this.io.oscClientGH.send("/building", JSON.stringify(_data));
    });

    socket.on("compute eui", (_data) => {
      if (!this.io.logs)
        this.io.logs = {
          euiCalculationTriggers: 0,
        };
      this.io.logs.euiCalculationTriggers++;
      this.io.oscClientGH.send("/computeEui", 1);
      const clearComputeFlag = () => {
        this.io.oscClientGH.send("/computeEui", 0);
      };
      setTimeout(clearComputeFlag.bind(this), 1000);
      console.log("computing eui");
    });

    socket.on("disconnect", () => this.disconnect());
    socket.on("connect_error", (err) => {
      console.log(`connect_error due to ${err.message}`);
    });
  }

  disconnect() {}
}

const chat = (io) => {
  io.on("connection", (socket) => {
    new Connection(io, socket);
  });

  io.oscServer = new Server(3334, "0.0.0.0", () => {
    console.log("OSC Server is listening");
  });

  io.oscServer.on("/0/cost", function (msg) {
    const address = msg[0];
    const cost = msg[1];
    io.emit("cost", cost);
  });

  io.oscServer.on("/0/eui", function (msg) {
    const address = msg[0];
    const eui = msg[1];
    io.emit("eui", eui);
  });
  io.oscServer.on("/0/results", function (msg) {
    const address = msg[0];
    const results = JSON.parse(msg[1]);
    io.emit("results", results);
  });

  io.oscServer.on("/response", function (msg) {
    //TODO: only broadcast to room members
    const address = msg[0];
    const response = JSON.parse(msg[1]);
    io.emit(response.ghCallback, response);
  });

  io.oscClientGH = new Client("127.0.0.1", 3333);
  io.oscClient = new Client("127.0.0.1", 3335);
};

module.exports = chat;
