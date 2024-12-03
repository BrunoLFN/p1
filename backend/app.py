from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

app = FastAPI()

# Função para converter ObjectId para string
def serialize_document(doc):
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc

# Configurar conexão com o MongoDB
client = AsyncIOMotorClient(
    'mongodb+srv://bruno:123@cluster0.de8ea.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
)
db = client.financial_goals_db

# Modelo de dados
class FinancialGoal(BaseModel):
    name: str
    target_amount: float = Field(gt=0, description="O valor alvo deve ser maior que zero.")
    current_amount: float = Field(ge=0, description="O valor atual deve ser maior ou igual a zero.")

class UpdateFunds(BaseModel):
    amount: float = Field(..., description="O valor a ser incrementado ou decrementado nos fundos.", ne=0)

# Criar meta
@app.post("/goals/", status_code=201)
async def create_goal(goal: FinancialGoal):
    new_goal = await db.goals.insert_one(goal.dict())
    return {"id": str(new_goal.inserted_id)}

# Listar metas
@app.get("/goals/")
async def list_goals(limit: int = 100, skip: int = 0):
    goals = await db.goals.find().skip(skip).limit(limit).to_list(length=limit)
    return [serialize_document(goal) for goal in goals]

# Obter meta por ID
@app.get("/goals/{goal_id}")
async def get_goal(goal_id: str):
    try:
        goal = await db.goals.find_one({"_id": ObjectId(goal_id)})
        if not goal:
            raise HTTPException(status_code=404, detail="Meta não encontrada")
        return serialize_document(goal)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

# Atualizar meta
@app.put("/goals/{goal_id}")
async def update_goal(goal_id: str, goal: FinancialGoal):
    try:
        result = await db.goals.update_one({"_id": ObjectId(goal_id)}, {"$set": goal.dict()})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Meta não encontrada")
        return {"message": "Meta atualizada"}
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

# Atualizar fundos
@app.patch("/goals/{goal_id}/funds/")
async def update_funds(goal_id: str, funds: UpdateFunds):
    try:
        goal = await db.goals.find_one({"_id": ObjectId(goal_id)})
        if not goal:
            raise HTTPException(status_code=404, detail="Meta não encontrada")
        new_amount = goal["current_amount"] + funds.amount
        if new_amount < 0:
            raise HTTPException(status_code=400, detail="Fundos insuficientes")
        await db.goals.update_one({"_id": ObjectId(goal_id)}, {"$set": {"current_amount": new_amount}})
        return {"message": "Fundos atualizados", "current_amount": new_amount}
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

# Excluir meta
@app.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str):
    try:
        result = await db.goals.delete_one({"_id": ObjectId(goal_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Meta não encontrada")
        return {"message": "Meta removida"}
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

# Obter totais
@app.get("/total/")
async def get_totals():
    try:
        goals = await list_goals()
        if not goals:
            raise HTTPException(status_code=404, detail="Metas não encontradas")
        current_total = sum(float(goal['current_amount']) for goal in goals)
        target_total = sum(float(goal['target_amount']) for goal in goals)
        return {"current_total": round(current_total, 2), "target_total": round(target_total, 2)}
    except Exception:
        raise HTTPException(status_code=400, detail="Erro ao calcular os totais.")