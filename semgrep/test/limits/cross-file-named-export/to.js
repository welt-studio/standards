import mongoose from "mongoose";
import { Account } from "./from";

const Local = mongoose.model("Local", new mongoose.Schema({}));

export function control(req) {
  // Controle: o modelo criado no mesmo arquivo é achado.
  return Local.find({ id: req.body.id });
}

export function search(req) {
  return Account.find({ id: req.body.id });
}
